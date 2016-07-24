from src.main.matrixelements import KineticEnergyMatrix
from src.main.matrixelements import NuclearAttractionMatrix
from src.main.matrixelements import OrbitalOverlapMatrix
from src.main.matrixelements import TwoElectronRepulsionMatrixOS
from src.main.hartreefock import LinearAlgebra
from src.main.hartreefock import BlockedLinearAlgebra
from src.main.hartreefock import RestrictedSCF
from src.main.hartreefock import DifferentOrbitalsDifferentSpins
from src.main.hartreefock import ConstrainedUnrestrictedSCF
from src.main.hartreefock import BlockedUnrestrictedSCF
from src.main.matrixelements import blocked_spin_basis_set
import numpy as np
import time


class HartreeFock:

    def __init__(self, nuclei_array, basis_set_array, electrons, symmetry, processes):
        self.nuclei_array = nuclei_array
        self.basis_set_array = basis_set_array
        self.electrons = electrons
        self.symmetry = symmetry
        self.orbital_overlap = OrbitalOverlapMatrix(basis_set_array).create()
        self.kinetic_energy = KineticEnergyMatrix(basis_set_array).create()
        self.nuclear_attraction = NuclearAttractionMatrix(basis_set_array, nuclei_array).create()
        self.core_hamiltonian = self.kinetic_energy + self.nuclear_attraction
        self.linear_algebra = LinearAlgebra(self.orbital_overlap)
        print('\n*************************************************************************************************')
        print('\nMATRICES\n')
        print('\nORBITAL OVERLAP MATRIX\n{}'.format(self.orbital_overlap))
        print('\nKINETIC ENERGY MATRIX\n{}'.format(self.kinetic_energy))
        print('\nNUCLEAR POTENTIAL ENERGY MATRIX\n{}'.format(self.nuclear_attraction))
        print('\nCORE HAMILTONIAN MATRIX\n{}'.format(self.core_hamiltonian))
        print('\nBEGIN TWO ELECTRON REPULSION CALCULATION')
        start_repulsion = time.clock()
        self.repulsion = TwoElectronRepulsionMatrixOS(self.basis_set_array, self.symmetry, processes).create()
        print('TIME TAKEN: ' + str(time.clock() - start_repulsion) + 's\n')
        print('\n*************************************************************************************************')

    def initial_guess(self):
        initial_orbital_energies, initial_orbital_coefficients = self.linear_algebra.diagonalize(self.core_hamiltonian)
        return initial_orbital_coefficients


class RestrictedHF(HartreeFock):

    def __init__(self, nuclei_array, basis_set_array, electrons, symmetry, processes):
        super().__init__(nuclei_array, basis_set_array, electrons, symmetry, processes)
        self.scf_method = RestrictedSCF(self.core_hamiltonian, self.linear_algebra, self.repulsion, self.electrons,
        self.orbital_overlap)

    def begin_scf(self):
        print('\n\nBEGIN RESTRICTED HARTREE FOCK\n')
        initial_coefficients = self.initial_guess()
        print('COEFFICIENTS INITIAL GUESS\n{}'.format(initial_coefficients))
        print('\n\nBEGIN SCF PROCEDURE')
        start = time.clock()
        electron_energy, orbital_energies, orbital_coefficients = self.scf_method.begin_iterations(initial_coefficients)
        print('TIME TAKEN: ' + str(time.clock() - start) + 's\n')
        print('\nORBITAL ENERGY EIGENVALUES\n{}'.format(orbital_energies))
        print('\nORBITAL COEFFICIENTS\n{}'.format(orbital_coefficients), end='\n\n\n')

        return electron_energy, orbital_energies, orbital_coefficients


class UnrestrictedHF(HartreeFock):

    def __init__(self, nuclei_array, basis_set_array, electrons, multiplicity, scf_method, symmetry, processes):
        super().__init__(nuclei_array, basis_set_array, electrons, symmetry, processes)
        self.scf_method = scf_method(self.core_hamiltonian, self.linear_algebra, self.repulsion, self.electrons,
        multiplicity)

    def begin_scf(self):
        print('\n\nBEGIN UNRESTRICTED HARTREE FOCK\n')
        initial_coefficients = self.initial_guess()
        print('COEFFICIENTS INITIAL GUESS\n{}'.format(initial_coefficients))
        print('\n\nBEGIN SCF PROCEDURE')
        start = time.clock()
        electron_energy, energies_alpha, energies_beta, coefficients_alpha, coefficients_beta \
            = self.scf_method.begin_iterations(initial_coefficients)
        print('TIME TAKEN: ' + str(time.clock() - start) + 's\n')
        print('\nALPHA ORBITAL ENERGY EIGENVALUES\n{}'.format(energies_alpha))
        print('\nBETA ORBITAL ENERGY EIGENVALUES\n{}'.format(energies_beta))
        print('\nALPHA ORBITAL COEFFICIENTS\n{}'.format(coefficients_alpha), end='\n')
        print('\nBETA ORBITAL COEFFICIENTS\n{}'.format(coefficients_beta), end='\n\n\n')

        return electron_energy, energies_alpha, energies_beta, coefficients_alpha, coefficients_beta


class DODSUnrestricted(UnrestrictedHF):

    def __init__(self, nuclei_array, basis_set_array, electrons, multiplicity, symmetry, processes):
        super().__init__(nuclei_array, basis_set_array, electrons, multiplicity, DifferentOrbitalsDifferentSpins,
        symmetry, processes)


class ConstrainedUnrestricted(UnrestrictedHF):

    def __init__(self, nuclei_array, basis_set_array, electrons, multiplicity, symmetry, processes):
        super().__init__(nuclei_array, basis_set_array, electrons, multiplicity, ConstrainedUnrestrictedSCF,
        symmetry, processes)


class BlockedHartreeFock(HartreeFock):

    def __init__(self, nuclei_array, basis_set_array, electrons, multiplicity, symmetry, processes):
        super().__init__(nuclei_array, basis_set_array, electrons, symmetry, processes)
        self.zeros = np.zeros((self.orbital_overlap.shape[0], self.orbital_overlap.shape[0]))

        self.orbital_overlap = np.bmat([
                [self.orbital_overlap, self.zeros],
                [self.zeros, self.orbital_overlap]
        ])

        self.core_hamiltonian = np.bmat([
                [self.core_hamiltonian, self.zeros],
                [self.zeros, self.core_hamiltonian]
        ])

        self.repulsion = blocked_spin_basis_set(self.repulsion)
        self.linear_algebra = BlockedLinearAlgebra(self.orbital_overlap)
        self.scf_method = BlockedUnrestrictedSCF(self.core_hamiltonian, self.linear_algebra,
        self.repulsion, self.electrons, multiplicity, self.orbital_overlap)

    def begin_scf(self):
        print('\n\nBEGIN BLOCKED UNRESTRICTED HARTREE FOCK\n')
        initial_coefficients = self.initial_guess()
        print('COEFFICIENTS INITIAL GUESS\n{}'.format(initial_coefficients))
        print('\n\nBEGIN SCF PROCEDURE')
        start = time.clock()
        electron_energy, orbital_energies, orbital_coefficients = self.scf_method.begin_iterations(initial_coefficients)
        print('TIME TAKEN: ' + str(time.clock() - start) + 's\n')
        print('\nORBITAL ENERGY EIGENVALUES\n{}'.format(orbital_energies))
        print('\nORBITAL COEFFICIENTS\n{}'.format(orbital_coefficients), end='\n\n\n')

        return electron_energy, orbital_energies, orbital_coefficients
