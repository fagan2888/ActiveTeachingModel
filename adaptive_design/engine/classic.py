import numpy as np

from scipy.special import logsumexp
from itertools import product


EPS = np.finfo(np.float).eps


class AdaptiveClassic:

    def __init__(self, learner_model, possible_design, grid_size=5):

        self.learner_model = learner_model

        self.n_param = len(self.learner_model.bounds)

        self.grid_size = grid_size

        self.possible_design = possible_design

        self.log_lik = np.zeros((len(self.possible_design),
                                 len(self.grid_param), 2))

        self.hist = []

        # Post <= prior
        lp = np.ones(len(self.grid_param))
        self.log_post = lp - logsumexp(lp)

        self.mutual_info = None

        self._compute_grid_param()

    def _compute_grid_param(self):

        self.grid_param = np.asarray(list(
            product(*[
                np.linspace(
                    *self.learner_model.bounds[key],
                    self.grid_size) for key in
                sorted(self.learner_model.bounds)])
        ))

    def reset(self):
        """
        Reset the engine as in the initial state.
        """

        # Reset the history
        self.hist = []

        # Reset the post / prior
        lp = np.ones(len(self.grid_param))
        self.log_post = lp - logsumexp(lp)

        self._compute_log_lik()

        self.mutual_info = None

        self._update_mutual_info()

    def _p_obs(self, item, param):

        learner = self.learner_model(
            t=len(self.hist),
            hist=self.hist,
            param=param)
        p_obs = learner.p_recall(item=item)
        return p_obs

    def _compute_log_lik(self):
        """Compute the log likelihood."""

        for i, x in enumerate(self.possible_design):
            for j, param in enumerate(self.grid_param):
                p = self._p_obs(x, param)
                for y in (0, 1):
                    self.log_lik[i, j, y] \
                        = y * np.log(p + EPS) + (1 - y) * np.log(1 - p + EPS)

    def _update_mutual_info(self):

        # If there is no need to update mutual information, it ends.
        if not self.flag_update_mutual_info:
            return

        # Calculate the marginal log likelihood.
        # shape (num_design, num_response)
        lp = self.log_post.reshape((1, len(self.log_post), 1))
        mll = logsumexp(self.log_lik + lp, axis=1)

        # Calculate the marginal entropy and conditional entropy.
        # Should be noted as the posterior, not marginal log likelihood
        # shape (num_designs,)
        ent_mrg = - np.sum(np.exp(mll) * mll, -1)

        # Compute conditional entropy
        # shape (num_designs,)
        ll = self.log_lik
        ent_obs = np.multiply(np.exp(ll), ll).sum(-1)
        ent_cond = - np.sum(
            self.post * ent_obs, axis=1)

        # Calculate the mutual information.
        # shape (num_designs,)
        self.mutual_info = ent_mrg - ent_cond

        # Flag that there is no need to update mutual information again.
        self.flag_update_mutual_info = False

    def get_design(self, kind='optimal'):
        # type: (str) -> int
        r"""
        Choose a design with a given type.

        * ``optimal``: an optimal design :math:`d^*` that maximizes the mutual
          information.
        * ``random``: a design randomly chosen.

        Parameters
        ----------
        kind : {'optimal', 'random'}, optional
            Type of a design to choose

        Returns
        -------
        design : int
            A chosen design
        """

        if kind == 'optimal':
            idx_design = np.argmax(self.mutual_info)
            design = self.possible_design[idx_design]
        elif kind == 'random':
            design = np.random.choice(self.possible_design)
        else:
            raise ValueError(
                'The argument kind should be "optimal" or "random".')
        return design

    def update(self, design, response):
        r"""
        Update the posterior :math:`p(\theta | y_\text{obs}(t), d^*)` for
        all discretized values of :math:`\theta`.

        .. math::
            p(\theta | y_\text{obs}(t), d^*) =
                \frac{ p( y_\text{obs}(t) | \theta, d^*) p_t(\theta) }
                    { p( y_\text{obs}(t) | d^* ) }

        Parameters
        ----------
        design
            Design vector for given response
        response
            0 or 1
        """

        idx_design = list(self.possible_design).index(design)

        self.log_post += self.log_lik[idx_design, :, response].flatten()
        self.log_post -= logsumexp(self.log_post)

        self.hist.append(design)
        self._compute_log_lik()
        self._update_mutual_info()

    @property
    def post(self) -> np.ndarray:
        """Posterior distributions of joint parameter space"""
        return np.exp(self.log_post)

    @property
    def post_mean(self) -> np.ndarray:
        """
        A vector of estimated means for the posterior distribution.
        Its length is ``num_params``.
        """
        return np.dot(self.post, self.grid_param)

    @property
    def post_cov(self) -> np.ndarray:
        """
        An estimated covariance matrix for the posterior distribution.
        Its shape is ``(num_grids, num_params)``.
        """
        # shape: (N_grids, N_param)
        d = self.grid_param - self.post_mean
        return np.dot(d.T, d * self.post.reshape(-1, 1))

    @property
    def post_sd(self) -> np.ndarray:
        """
        A vector of estimated standard deviations for the posterior
        distribution. Its length is ``num_params``.
        """
        return np.sqrt(np.diag(self.post_cov))
