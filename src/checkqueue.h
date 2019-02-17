// Copyright (c) 2012-2018 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef BITCOIN_CHECKQUEUE_H
#define BITCOIN_CHECKQUEUE_H

#include <sync.h>

#include <util/system.h>

#include <algorithm>
#include <vector>

template <typename T>
class CCheckQueueControl;

/**
 * Queue for verifications that have to be performed.
  * The verifications are represented by a type T, which must provide an
  * operator(), returning a bool.
  *
  * One thread (the master) is assumed to push batches of verifications
  * onto the queue, where they are processed by N-1 worker threads. When
  * the master is done adding work, it temporarily joins the worker pool
  * as an N'th worker, until all jobs are done.
  */
template <typename T>
class CCheckQueue
{
private:
    //! Mutex to protect the inner state
    Mutex mutex;

    //! Worker threads block on this when out of work
    std::condition_variable condWorker;

    //! Master thread blocks on this when out of work
    std::condition_variable condMaster;

    //! The queue of elements to be processed.
    //! As the order of booleans doesn't matter, it is used as a LIFO (stack)
    std::vector<T> queue GUARDED_BY(mutex);

    //! The worker threads
    std::vector<std::thread> m_threads;

    //! The total number of workers (including the master).
    int nTotal = 0;

    //! The temporary evaluation result.
    bool fAllOk GUARDED_BY(mutex) = true;

    //! The interrupt flag.
    std::atomic<bool> interrupted{false};

    std::atomic<unsigned int> nIndex{ 0 };

    /**
     * Number of verifications that haven't completed yet.
     * This includes elements that are no longer queued, but still in the
     * worker's own batches.
     */
    std::atomic<unsigned int> nTodo{ 0 };

    //! The maximum number of elements to be processed in one batch
    const unsigned int nBatchSize;

    /** Internal function that does bulk of the verification work. */
    bool Loop(const bool fMaster = false)
    {
        bool fOk = true;
        while (true) {
            int index = nIndex.fetch_add(1, std::memory_order_acq_rel);
            if (index < nTotal) {
                fOk &= queue[index]();
                nTodo.fetch_sub(1, std::memory_order_acquire);
            }
            else {
                WAIT_LOCK(mutex, lock);
                if (fMaster) {
                    condMaster.wait(lock, [this]() EXCLUSIVE_LOCKS_REQUIRED(mutex) {
                        return nTodo.load(std::memory_order_release) == 0;
                    });
                    bool fRet = fAllOk;
                    fAllOk = true;
                    return fRet;
                }
                else {
                    fAllOk &= fOk;
                    if (nTodo.load(std::memory_order_release) == 0) {
                        condMaster.notify_one();
                    }
                    if (interrupted.load(std::memory_order_release)) {
                        return true;
                    }
                    condWorker.wait(lock, [this]() EXCLUSIVE_LOCKS_REQUIRED(mutex) { 
                        return interrupted.load(std::memory_order_release) || nIndex.load(std::memory_order_release) < nTotal;
                    });
                    fOk = true;
                }
            }
        }
    }

public:
    //! Mutex to ensure only one concurrent CCheckQueueControl
    Mutex ControlMutex;

    //! Create a new check queue
    explicit CCheckQueue(unsigned int nBatchSizeIn) : nBatchSize(nBatchSizeIn) {}

    //! Wait until execution finishes, and return whether all evaluations were successful.
    bool Wait()
    {
        return Loop(true);
    }

    //! Add a batch of checks to the queue
    void Add(std::vector<T>& vChecks)
    {
        LOCK(mutex);
        for (T& check : vChecks) {
            queue.push_back(T());
            check.swap(queue.back());
        }
        nTodo.fetch_add(vChecks.size(), std::memory_order_acq_rel);
        nIndex.store(0, std::memory_order_acq_rel);
        if (vChecks.size() == 1)
            condWorker.notify_one();
        else if (vChecks.size() > 1)
            condWorker.notify_all();
    }

    void Start(const int n_threads, const char* const thread_name = nullptr)
    {
        assert(m_threads.size() == 0);
        interrupted.store(false , std::memory_order_acquire);
        if (n_threads <= 0) return;
        m_threads.reserve(n_threads);
        for (int i = 0; i < n_threads; i++) {
            m_threads.emplace_back([thread_name, this] {
                if (thread_name != nullptr) RenameThread(thread_name);
                Loop();
            });
        }
    }

    void Interrupt()
    {
        interrupted.store(true, std::memory_order_acq_rel);
        condWorker.notify_all();
    }

    void Stop()
    {
        for (std::thread& thread : m_threads) {
            thread.join();
        }
        m_threads.clear();
    }

    ~CCheckQueue()
    {
    }
};

/**
 * RAII-style controller object for a CCheckQueue that guarantees the passed
 * queue is finished before continuing.
 */
template <typename T>
class CCheckQueueControl
{
private:
    CCheckQueue<T> * const pqueue;
    bool fDone;

public:
    CCheckQueueControl() = delete;
    CCheckQueueControl(const CCheckQueueControl&) = delete;
    CCheckQueueControl& operator=(const CCheckQueueControl&) = delete;
    explicit CCheckQueueControl(CCheckQueue<T> * const pqueueIn) : pqueue(pqueueIn), fDone(false)
    {
        // passed queue is supposed to be unused, or nullptr
        if (pqueue != nullptr) {
            ENTER_CRITICAL_SECTION(pqueue->ControlMutex);
        }
    }

    bool Wait()
    {
        if (pqueue == nullptr)
            return true;
        bool fRet = pqueue->Wait();
        fDone = true;
        return fRet;
    }

    void Add(std::vector<T>& vChecks)
    {
        if (pqueue != nullptr)
            pqueue->Add(vChecks);
    }

    ~CCheckQueueControl()
    {
        if (!fDone)
            Wait();
        if (pqueue != nullptr) {
            LEAVE_CRITICAL_SECTION(pqueue->ControlMutex);
        }
    }
};

#endif // BITCOIN_CHECKQUEUE_H
