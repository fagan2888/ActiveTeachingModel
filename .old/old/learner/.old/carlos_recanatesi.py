import os
import pickle

import numpy as np
from tqdm import tqdm

import plot.oscillating_attractor_networks

np.seterr(all='raise')


class Network:
    """
    # Architecture
    :param n_neurons: int total number of neurons. "N" in the original article.
    :param p: int number of memories.

    # Activation Function
    :param tau: float decay time.

    # Gain Function
    :param theta: gain function threshold.
    :param gamma: float gain func exponent. Always sub-linear, then value < 1.

    # Hebbian Rule
    :param kappa: excitation parameter.
    :param f: sparsity of bit probability.

    # Inhibition Parameter Calculation
    :param phi_min: float inhibition parameter minimum value.
    :param phi_max: float inhibition parameter maximum value.
    :param tau_0: oscillation time.

    # Short Term Association of Items
    :param j_forward: forward contiguity.
    :param j_backward: backward contiguity.

    # Time-related Attributes
    :param t_tot: total time when working on continuous time.
    :param dt: float integration time step.

    # Not Yet Classified
    :param xi_0: noise variance.
    :param r_ini: initial rate. All neurons belonging to memory mu are
    initialized to this value. Others are set to 0.


    Gives the parameters to the network. Default values as listed in Recanatesi
    (2015).

    2019 07 31: Good enough parameters are
                param={
                "num_neurons": 150,  #int(10**5*factor),
                "f": 0.1,
                "p": 4,
                "xi_0": 65, #65,  # 65*factor,
                "kappa": 13000,  # 13*10**3*factor,
                "t_tot": 10,
                "tau_0": 1,
                "gamma": 2/5,
                "phi_min": 0.7,
                "phi_max": 1.06,
                "phase_shift": 0.25,
            })
    """

    def __init__(
            self,
            # Architecture ###########
            n_neurons=100000,
            p=16,
            # Activation #############
            tau=0.01,
            # Gain ###################
            theta=0,
            gamma=0.4,
            # Hebbian rule ###########
            kappa=13000,
            f=0.01,
            # Inhibition #############
            phi_min=0.70,
            phi_max=1.06,
            tau_0=1,
            phase_shift=0.0,
            # Short term association #
            j_forward=1500,
            j_backward=400,
            # Time ###################
            t_tot=450,
            dt=0.001,
            # Noise #####
            xi_0=65,
            # Initialization #########
            r_ini=1,
            first_p=1
    ):
        # r_threshold=15,
        # n_trials=10000,
        # r_ini=1,):

        # Architecture
        self.n_neurons = n_neurons
        self.p = p

        # Activation function
        self.tau = tau

        # Gain function
        self.theta = theta
        self.gamma = gamma

        # Hebbian rule
        self.kappa = kappa
        self.f = f

        # Inhibition
        self.phi_min = phi_min
        self.phi_max = phi_max
        assert phi_max > phi_min
        self.tau_0 = tau_0

        # Short term association
        self.j_forward = j_forward
        self.j_backward = j_backward

        # Time
        self.t_tot = t_tot
        self.dt = dt

        self.phase_shift = phase_shift

        # Noise parameter
        self.xi_0 = xi_0

        # Initialization
        self.r_ini = r_ini
        self.first_p = first_p

        # Not implemented
        # self.r_threshold = r_threshold
        # self.n_trials = n_trials

        self.connectivity = \
            np.random.choice([0, 1], p=[1 - self.f, self.f],
                             size=(self.p, self.n_neurons))

        self.activation = np.zeros(self.n_neurons)

        self.t_tot_discrete = int(self.t_tot / self.dt)

        self.average_firing_rate = np.zeros((self.p, self.t_tot_discrete))

        self.kappa_over_n = self.kappa / self.n_neurons

        self.weights_constant = np.zeros((self.n_neurons,
                                          self.n_neurons))

        self.delta_weights = np.zeros((self.n_neurons,
                                       self.n_neurons))

        self.phi = None

    @staticmethod
    def _sinusoid(min_, max_, period, t, phase_shift, dt=1.):

        amplitude = (max_ - min_) / 2
        frequency = (1 / period) * dt
        shift = min_ + amplitude  # Moves the wave in the y-axis

        return \
            amplitude \
            * np.sin(2 * np.pi * (t + phase_shift / dt) * frequency) \
            + shift

    def _update_phi(self, t):
        """
        Phi is a sinusoid function related to neuron inhibition.
        It follows the general sine wave function:
            f(x) = amplitude * (2 * pi * frequency * time)
        In order to adapt to the phi_min and phi_max parameters the amplitude
        and an additive shift term have to change.
        Frequency in discrete time has to be adapted from the given tau_0
        period in continuous time.

        :param t: int discrete time step.
        """
        self.phi = self._sinusoid(
            min_=self.phi_min,
            max_=self.phi_max,
            period=self.tau_0,
            t=t,
            phase_shift=self.phase_shift * self.tau_0,
            dt=self.dt
        )

    def _present_pattern(self):

        self.activation[:] = self.connectivity[self.first_p, :] \
                             * self.r_ini

    def _g(self, current):

        if current + self.theta > 0:
            gain = (current + self.theta) ** self.gamma
        else:
            gain = 0

        return gain

    def _gaussian_noise(self):
        """ Variance has to be transformed into standard deviation. """
        return np.random.normal(loc=0, scale=self.xi_0 ** 0.5)

    def _compute_weight_constants(self):

        print("Computing weight constants...")
        for i in tqdm(range(self.n_neurons)):
            for j in range(self.n_neurons):

                sum_ = 0
                for mu in range(self.p):
                    sum_ += \
                        (self.connectivity[mu, i] - self.f) \
                        * (self.connectivity[mu, j] - self.f)

                self.weights_constant[i, j] = \
                    self.kappa_over_n * sum_

    def _compute_delta_weights(self):

        print("Computing delta weights...")
        for i in tqdm(range(self.n_neurons)):

            for j in range(self.n_neurons):

                # Sum for positive
                sum_pos = 0
                for mu in range(self.p - 1):
                    sum_pos += \
                        self.connectivity[mu, i] \
                        * self.connectivity[mu + 1, j]

                # Sum for negative
                sum_neg = 0
                for mu in range(1, self.p):
                    sum_neg += \
                        self.connectivity[mu, i] \
                        * self.connectivity[mu - 1, j]

                self.delta_weights[i, j] = \
                    self.j_forward * sum_pos \
                    + self.j_backward * sum_neg

    def _update_activation(self):

        new_current = np.zeros(self.activation.shape)

        for i in range(self.n_neurons):

            current = self.activation[i]
            noise = self._gaussian_noise()

            sum_ = 0
            for j in range(self.n_neurons):
                sum_ += \
                    (self.weights_constant[i, j]
                     - self.kappa_over_n * self.phi
                     + self.delta_weights[i, j]) \
                    * self._g(self.activation[j])

            business = sum_ + noise

            second_part = business * \
                (self.dt / self.tau)

            first_part = current * \
                (1 - (self.dt / self.tau))

            new_current[i] = first_part + second_part

        self.activation[:] = new_current

    def _save_fr(self, t):

        for mu in range(self.p):

            neurons = self.connectivity[mu, :]

            encoding = np.nonzero(neurons)[0]

            v = np.zeros(len(encoding))
            for i, n in enumerate(encoding):
                v[i] = self._g(self.activation[n])

            try:
                self.average_firing_rate[mu, t] = np.mean(v)
            except FloatingPointError:
                self.average_firing_rate[mu, t] = 0

    def _initialize(self):
        """
        Performs the following initial operations:
        * Update the inhibition parameter for time step 0.
        * Updates weights according using the previous connectivity matrix
        * Gives a random seeded pattern as the initial activation vector.
        * Updates the network for the total discrete time steps.
        """

        self._compute_weight_constants()
        self._compute_delta_weights()
        self._present_pattern()

    def simulate(self):
        self._initialize()

        print(f"Simulating for {self.t_tot_discrete} time steps...\n")
        for t in tqdm(range(self.t_tot_discrete)):
            self._update_phi(t)
            self._update_activation()
            self._save_fr(t)


def main(force=False):

    bkp_file = f'bkp/hopfield.p'

    os.makedirs(os.path.dirname(bkp_file), exist_ok=True)

    if not os.path.exists(bkp_file) or force:

        np.random.seed(1234)

        factor = 10**(-3)

        network = Network(
                n_neurons=int(10**5*factor),
                f=0.1,
                p=16,
                xi_0=65,
                kappa=13000,
                tau_0=1,
                gamma=2 / 5,
                phi_min=0.7,
                phi_max=1.06,
                phase_shift=0.75,
                j_forward=1500*factor,
                j_backward=400*factor,
                first_p=0,
                t_tot=4,
            )

        network.simulate()

        pickle.dump(network, open(bkp_file, 'wb'))
    else:
        print('Loading from pickle file...')
        network = pickle.load(open(bkp_file, 'rb'))

    plot.oscillating_attractor_networks.plot_phi(network)
    plot.oscillating_attractor_networks.plot_average_firing_rate(network)
    plot.oscillating_attractor_networks.plot_attractors(network)


if __name__ == "__main__":
    main(force=True)
