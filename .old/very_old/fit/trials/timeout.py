from pyGPGO.covfunc import squaredExponential
from pyGPGO.acquisition import Acquisition
from pyGPGO.surrogates.GaussianProcess import GaussianProcess
from pyGPGO.GPGO import GPGO, EventLogger

import multiprocessing as mp

import numpy as np

import queue

from fit.pygpgo.objective import objective
from fit.pygpgo.classic import PYGPGOFit


class TimeOutGPGO(mp.Process, GPGO):

    def __init__(self,
                 gp, acq, param,
                 queue_in, queue_out,
                 verbose,
                 init_evals):

        mp.Process.__init__(self)
        # GPGO.__init__(self, gp, acq, self.objective, param, n_jobs=1)

        self.verbose = verbose

        self.queue_in = queue_in
        self.queue_out = queue_out

        self.stop = False

        self.best_param = None
        self.best_value = None
        self.eval_param = None

        self.model, self.tk, self.data = None, None, None

        self.init_evals = init_evals

        # super().__init__(surrogate, acquisition, f, parameter_dict, n_jobs)

        self.GP = gp  # surrogate
        self.A = acq  # acquisition
        # self.f = self.objective
        self.parameters = param  # parameter_dict
        self.n_jobs = 2

        self.parameter_key = list(param.keys())
        self.parameter_value = list(param.values())
        self.parameter_type = [p[0] for p in self.parameter_value]
        self.parameter_range = [p[1] for p in self.parameter_value]

        self.history = []

        self.verbose = verbose
        if verbose:
            self.logger = EventLogger(self)

    def run(self):
        """
        Runs the Bayesian Optimization procedure.

        """

        self.model, self.tk, self.data = self.queue_in.get()

        while True:
            if self.stop:
                break

            self.eval_param = []

            self._firstRun(n_eval=self.init_evals, init_param=self.best_param)

            self._update_best()

            if self.verbose:
                self.logger._printInit(self)

            if self._should_i_restart():
                continue

            while True:
                self._optimizeAcq()
                self.updateGP()

                self._update_best()

                if self.verbose:
                    self.logger._printCurrent(self)

                if self._should_i_restart():
                    break

    def _firstRun(self, n_eval=3, init_param=None):
        """
        Performs initial evaluations before fitting GP.

        Parameters
        ----------
        n_eval: int
            Number of initial evaluations to perform. Default is 3.

        """
        self.X = np.empty((n_eval, len(self.parameter_key)))
        self.y = np.empty((n_eval,))

        if init_param is not None:
            s_param = init_param
            s_param_val = [s_param[k] for k in self.parameter_key]
            self.X[0] = s_param_val
            self.y[0] = self.f(**s_param)

            iterator = range(1, n_eval)

        else:
            iterator = range(0, n_eval)

        for i in iterator:
            s_param = self._sampleParam()
            s_param_val = list(s_param.values())
            self.X[i] = s_param_val
            self.y[i] = self.f(**s_param)

        self.GP.fit(self.X, self.y)
        self.tau = np.max(self.y)
        self.history.append(self.tau)

    def _should_i_restart(self):

        try:
            e = self.queue_in.get_nowait()
            if e == 'restart':
                self.model, self.tk, self.data = self.queue_in.get()
                return True

            if e == 'stop':
                self.stop = True
                return True

            elif e == 'get':
                self.queue_out.put(
                    (self.best_param, self.best_value, self.eval_param))

            else:
                print(e)
                raise Exception

        except queue.Empty:
            pass

    def _update_best(self):

        r = self.getResult()
        self.best_param = dict(r[0])
        self.best_value = r[1]

    def f(self, **param):

        value = objective(model=self.model, tk=self.tk, data=self.data,
                          param=param)
        self.eval_param.append(param)
        return value


class PYGPGOTimeoutFit(PYGPGOFit):

    def __init__(self, timeout=2, init_evals=3, verbose=False):

        super().__init__(init_evals=init_evals,  verbose=verbose)

        self.timeout = timeout

        self.opt = None

        self.queue_in = None
        self.queue_out = None

    def evaluate(self, data, model, tk):

        if self.opt is None:

            self.queue_in = mp.Queue()
            self.queue_out = mp.Queue()

            param = {
                f'{b[0]}': ('cont', [b[1], b[2]])
                for b in model.bounds
            }

            sexp = squaredExponential()
            gp = GaussianProcess(sexp)

            # surrogate = BoostedTrees()
            acq = Acquisition(mode='ExpectedImprovement')

            self.opt = TimeOutGPGO(
                gp=gp, acq=acq, param=param,
                queue_in=self.queue_in,
                queue_out=self.queue_out,
                init_evals=self.init_evals,
                verbose=self.verbose
            )
            self.opt.start()

        else:
            self.queue_in.put('restart')

        self.queue_in.put((model, tk, data))

        mp.Event().wait(timeout=self.timeout)

        self.queue_in.put('get')

        self.best_param, self.best_value, self.eval_param = \
            self.queue_out.get()

        self.hist_best_param.append(self.best_param)
        self.hist_best_value.append(self.best_value)

        return self.best_param

    def stop(self):

        self.queue_in.put('stop')
