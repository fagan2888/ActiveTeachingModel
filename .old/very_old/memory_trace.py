import plot.memory_trace
from learner.act_r import ActR

from behavior.data_structure import Task

from simulation.memory import p_recall_over_time_after_learning

import datetime

import numpy as np


def main_continuous(n_iteration=100, n_item=9):

    total_time = datetime.timedelta(days=10)
    sec = int(total_time.total_seconds())

    time_norm = n_iteration/sec

    time = np.random.randint(low=0, high=sec, size=n_iteration)
    time.sort()

    questions = np.random.randint(low=0, high=n_item, size=n_iteration)

    success = np.zeros(n_iteration, dtype=bool)

    agent = ActR(
        param={"d": 0.5, "tau": 0.01, "s": 0.06},
        tk=Task(n_iteration=n_iteration, n_item=n_item))

    for i in range(n_iteration):

        item, t = questions[i], time[i]

        p = agent.p(item=item, time=t * time_norm)
        r = np.random.random()

        success[i] = p > r

        agent.learn(item=item, time=t * time_norm)

    time_sampling = np.linspace(start=0, stop=sec, num=100)

    p_recall = p_recall_over_time_after_learning(agent=agent,
                                                 n_iteration=n_iteration,
                                                 n_item=n_item,
                                                 time_norm=time_norm,
                                                 time_sampling=time_sampling)

    plot.memory_trace.plot(p_recall_value=p_recall,
                           p_recall_time=time_sampling,
                           success_time=time,
                           success_value=success,
                           questions=questions)

    plot.memory_trace.summarize(p_recall=p_recall,
                                p_recall_time=time_sampling)


def main_discrete(n_iteration=100, n_item=9):

    questions = np.random.randint(low=0, high=n_item, size=n_iteration)
    seen = np.zeros((n_item, n_iteration), dtype=bool)
    success = np.zeros(n_iteration, dtype=bool)

    agent = ActR(
        param={"d": 0.5, "tau": 0.01, "s": 0.06},
        tk=Task(n_iteration=n_iteration, n_item=n_item))

    for t in range(n_iteration):

        item = questions[t]

        p = agent.p(item=item)
        r = np.random.random()

        success[t] = p > r

        agent.learn(item=item)

        if t:
            seen[:, t] = seen[:, t-1]

        seen[item, t] = 1

    p_recall = p_recall_over_time_after_learning(agent=agent,
                                                 n_iteration=n_iteration,
                                                 n_item=n_item)

    plot.memory_trace.plot(p_recall_value=p_recall,
                           success_value=success,
                           questions=questions)

    plot.memory_trace.summarize(p_recall=p_recall)

    plot.memory_trace.summarize_over_seen(p_recall=p_recall, seen=seen)


if __name__ == "__main__":
    main_discrete()
