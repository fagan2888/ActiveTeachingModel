import os
import pickle

import numpy as np
from tqdm import tqdm

import plot.attractor_networks
# from learner.carlos_recanatesi import Network

np.seterr(all='raise')


class SimplifiedNetwork:
    """
    Simplified version of the network by Recanatesi (2015). A dimensionality
    reduction reduces the number of simulated units.
    """

    def __init__(
            self,
            # Architecture ###########
            n_neuron=100000,
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
            n_trials=10000,
            # Noise #####
            xi_0=65,
            # Initialization #########
            r_ini=1,
            first_p=1
    ):

        # Architecture
        self.n_neuron = n_neuron
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
        self.phase_shift = phase_shift

        # Short term association
        self.j_forward = j_forward
        self.j_backward = j_backward

        # Time
        self.t_tot = t_tot
        self.dt = dt
        self.n_trials = n_trials

        # Noise parameter
        self.xi_0 = xi_0

        # Initialization
        self.r_ini = r_ini
        self.first_p = first_p

        # General pre-computations
        self.t_tot_discrete = int(self.t_tot / self.dt)
        self.phi = np.zeros(self.t_tot_discrete)
        self.relative_excitation = self.kappa / self.n_neuron

        # Unique simplified network attributes
        memory_patterns = \
            np.random.choice([0, 1], p=[1 - self.f, self.f],
                             size=(self.p, self.n_neuron))
        self.unique_patterns, self.pre_neurons_per_pattern = \
            np.unique(memory_patterns, axis=1, return_counts=True)
        self.s = self.pre_neurons_per_pattern / self.n_neuron

        self.n_population = self.unique_patterns.shape[1]

        # self.n_neurons = self.n_population  # Reduce the number of
        # neurons after computing v, w

        self.noise_amplitudes = np.zeros(self.n_population)
        self.noise_values = np.zeros((self.n_population, self.t_tot))

        self.connectivity_matrix = np.zeros((
            self.n_population, self.n_population))

        self.sam_connectivity = np.zeros((self.n_population,
                                          self.n_population))
        self.activation = np.zeros(self.n_population)

        self.population_currents = np.zeros(self.n_population)

        # Plotting
        self.average_firing_rate = np.zeros((self.p, self.t_tot_discrete))

    def _present_pattern(self):
        """
        Activation vector will be one pattern for one memory multiplied
        by a parameter whose default value is usually 1.
        """

        self.activation[:] = self.unique_patterns[self.first_p, :] \
            * self.r_ini  # CHECK

    def _compute_gaussian_noise(self):
        """Amplitude of uncorrelated Gaussian noise is its variance"""
        # YES
        self.amplitude = self.xi_0 * self.s * self.n_neuron

        for i in range(self.n_population):
            # Double check
            self.noise_values[i] = \
                np.random.normal(loc=0,
                                 scale=self.amplitude[i],
                                 size=self.t_tot)

    def _compute_connectivity_matrix(self, t):
        """
        Weights do not change in this network architecture and can therefore
        be pre-computed.
        """
        # YES

        print("Computing weights...")
        for i in tqdm(range(self.n_population)):
            for j in range(self.n_population):

                sum_ = 0
                for mu in range(self.p):
                    sum_ += \
                        (self.unique_patterns[mu, i] - self.f) \
                        * (self.unique_patterns[mu, j] - self.f) - self.phi[t]

                self.connectivity_matrix[i, j] = \
                    self.relative_excitation * sum_

                if i == j:
                    self.connectivity_matrix[i, j] = 0

    def _compute_sam_connectivity(self):
        # YES

        print("Computing SAM connectivity...")
        for v in tqdm(range(self.n_population)):

            for w in range(self.n_population):

                # Sum for forward
                sum_forward = 0
                for mu in range(self.p - 1):
                    sum_forward += \
                        self.unique_patterns[mu, v] \
                        * self.unique_patterns[mu + 1, w]

                # Sum for backward
                sum_backward = 0
                for mu in range(1, self.p):
                    sum_backward += \
                        self.unique_patterns[mu, v] \
                        * self.unique_patterns[mu - 1, w]

                self.sam_connectivity[v, w] = \
                    self.j_forward * sum_forward \
                    + self.j_backward * sum_backward

    def _update_activation(self, t):
        """
        Method is iterated every time step and will compute for every pattern.
        Current of population v at time t+dt results from the addition of the
        three terms 'first_term', 'second_term', 'third_term'.
        !!!!!! TIME DEPENDENCY INCLUDED IN THE CONNECTIVITY (OR WEIGHTS)
        CALCULATION, CANNOT BE PRECOMPUTED
        """

        # new_current = np.zeros(self.activation.shape)

        for v in range(self.n_population):

            # current = self.activation[population]
            current = self.population_currents[v]

            # First
            first_term = current * (1 - self.dt)  # YES

            # Second


            sum_ = 0
            for w in range(self.n_population):
                sum_ += \
                    (self.connectivity_matrix[v, w]
                     - self.relative_excitation
                     * self.phi  # MISTAKE
                     + self.sam_connectivity[v, w]) \
                    * self._g(self.population_currents[w]) \
                    * self.s[w]

            second_term = sum_ * self.dt  # YES

            # Third
            third_term = self.noise_values[v, t] * self.dt  # YES

            self.population_currents[v] =\
                first_term + second_term + third_term
            # YES

        # self.activation[:] = new_current
        # self.population_currents[v] = new_current

    def _initialize(self):
        self._compute_phi()
        # self._compute_connectivity_matrix()
        self._present_pattern()
        self._compute_gaussian_noise()

    def _save_fr(self, t):

        for mu in range(self.p):

            neurons = self.unique_patterns[mu, :]

            encoding = np.nonzero(neurons)[0]

            v = np.zeros(len(encoding))
            for i, n in enumerate(encoding):
                v[i] = self._g(self.activation[n])

            try:
                self.average_firing_rate[mu, t] = np.mean(v)
            except FloatingPointError:
                self.average_firing_rate[mu, t] = 0

    @staticmethod
    def _sinusoid(min_, max_, period, t, phase_shift, dt=1.):
        """
        Phi is a sinusoid function related to neuron inhibition.
        It follows the general sine wave function:
            f(x) = amplitude * (2 * pi * frequency * time)
        In order to adapt to the phi_min and phi_max parameters the amplitude
        and an additive shift term have to change.
        Frequency in discrete time has to be adapted from the given tau_0
        period in continuous time.
        """
        amplitude = (max_ - min_) / 2
        frequency = (1 / period) * dt
        shift = min_ + amplitude  # Moves the wave in the y-axis

        return \
            amplitude \
            * np.sin(2 * np.pi * (t + phase_shift / dt) * frequency) \
            + shift

    def _compute_phi(self):

        for t in self.t_tot_discrete:
            self.phi[t] = self._sinusoid(
                min_=self.phi_min,
                max_=self.phi_max,
                period=self.tau_0,
                t=t,
                phase_shift=self.phase_shift * self.tau_0,
                dt=self.dt
            )

    def _g(self, current):

        if current + self.theta > 0:
            gain = (current + self.theta)**self.gamma
        else:
            gain = 0

        return gain

    def simulate(self):
        self._initialize()

        print(f"Simulating for {self.t_tot_discrete} time steps...\n")
        for t in tqdm(range(self.t_tot_discrete)):
            self._update_activation(t)
            self._save_fr(t)


def main(force=False):

    bkp_file = f'bkp/hopfield.p'

    os.makedirs(os.path.dirname(bkp_file), exist_ok=True)

    if not os.path.exists(bkp_file) or force:

        np.random.seed(123)

        # factor = 10**(-4)

        simplified_network = SimplifiedNetwork(
                n_neuron=int(10 ** 5),
                f=0.1,
                p=16,
                xi_0=65,
                kappa=13000,
                tau_0=1,
                gamma=2 / 5,
                phi_min=0.7,
                phi_max=1.06,
                phase_shift=0,
                j_forward=1500,
                j_backward=400,
                first_p=1,
                t_tot=12,
                n_trials=3
            )

        simplified_network.simulate()

        pickle.dump(simplified_network, open(bkp_file, 'wb'))
    else:
        print('Loading from pickle file...')
        simplified_network = pickle.load(open(bkp_file, 'rb'))

    # plot.attractor_networks.plot_phi(simplified_network)
    plot.attractor_networks.plot_average_firing_rate(simplified_network)
    plot.attractor_networks.plot_attractors(simplified_network)


if __name__ == "__main__":
    main(force=True)
