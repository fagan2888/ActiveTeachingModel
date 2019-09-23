import numpy as np

import GPyOpt

from . objective import objective


class Psychologist:

    def __init__(self,
                 student_model,
                 task_param,
                 testing_period=None, exploration_ratio=None,
                 exploration_threshold=None,
                 initial_design_numdata=10, max_iter=1000,
                 max_time=5):

        self.initial_design_numdata = initial_design_numdata
        self.max_iter = max_iter
        self.max_time = max_time

        self.task_param = task_param

        self.testing_period = testing_period
        self.exploration_ratio = exploration_ratio
        self.exploration_threshold = exploration_threshold

        self.student_model = student_model

        self.hist_item = None
        self.hist_success = None
        self.t = None

        self.hist_values = None
        self.hist_param = None

        self.hist_best_values = []
        self.hist_best_param = []

        self.best_param = None
        self.best_value = None
        self.estimated_var = None

    def _objective(self, param, keep_in_history=True):

        param = param[0]

        value = objective(
            model=self.student_model,
            hist_success=self.hist_success,
            hist_item=self.hist_item,
            task_param=self.task_param,
            t=self.t,
            param=param
        )

        if keep_in_history:
            self.hist_values.append(value)
            self.hist_param.append(param)
        return value

    def most_informative(
            self,
            hist_item,
            hist_success,
            n_item,
            n_iteration,
            task_param,
            t
    ):

        self.hist_item = hist_item
        self.hist_success = hist_success

        n_param_set = len(self.hist_param)

        p_recall = np.zeros((n_item, n_param_set))
        for j in range(n_param_set):

            param = self.hist_param[j]

            agent = self.student_model(
                param=param,
                n_iteration=n_iteration,
                hist=self.hist_item,
                t=t,
                **task_param)

            for i in range(n_item):
                agent.learn(i)
                p_recall[i, j] = agent.p_recall(i)
                agent.unlearn()

        std_per_item = np.std(p_recall, axis=1)

        max_std = np.max(std_per_item)
        if max_std == 0:
            non_seen_item = np.where(p_recall == 0)[0]
            return np.random.choice(non_seen_item)

        else:
            max_std_items = np.where(std_per_item == max_std)[0]
            return np.random.choice(max_std_items)

    def is_time_for_exploration(self, t):

        if t == 0:
            return False
        elif t == 1:
            return True
        elif t == 2:
            return False

        assert self.exploration_ratio is None \
            or self.exploration_threshold is not None, \
            "Choose one or the other!"
        if self.exploration_ratio is not None:

            if t < self.testing_period:
                exploration = t % 2 == 1

            else:
                exploration = np.random.random() <= self.exploration_ratio

        else:
            exploration = self.estimated_var >= self.exploration_threshold

        return exploration

    def update_estimates(self, hist_item, hist_success, t):

        self.hist_values = []
        self.hist_param = []

        bounds = [
            {'name': f'{b[0]}',
             'type': 'continuous',
             'domain': (b[1], b[2])
             } for b in self.student_model.bounds
        ]

        self.hist_item = hist_item
        self.hist_success = hist_success
        self.t = t

        myBopt = GPyOpt.methods.BayesianOptimization(
            f=self._objective, domain=bounds, acquisition_type='EI',
            exact_feval=False,
            initial_design_numdata=self.initial_design_numdata,
            normalize_Y=False)
        max_iter = np.inf
        max_time = 5
        eps = 10e-6

        myBopt.run_optimization(max_iter=max_iter,
                                max_time=max_time,
                                eps=eps)

        best_param_list = myBopt.x_opt
        self.best_param = {b[0]: v for b, v in
                           zip(self.student_model.bounds,
                               best_param_list)}

        self.best_value = myBopt.fx_opt

        model = myBopt.model.model
        eval_points = np.zeros((1, len(self.student_model.bounds)))
        eval_points[0, :] = myBopt.x_opt
        m, v = model.predict(eval_points)
        self.estimated_var = v[0][0]
        # print(np.array(self.hist_param).shape)
        # eval_points = np.array(self.hist_param)
        # m, v = model.predict(eval_points)
        # for i, m_i, v_i in zip(eval_points, m, v):
        #
        #     if (i == myBopt.x_opt).all():
        #         # print(i, m_i[0], v_i[0])
        #         print(v_i[0])
        self.hist_best_param.append(self.best_param)
        self.hist_best_values.append(self.best_value)

        print("BEST PARAM", self.best_param)

        return self.best_param
