# -*- coding: utf-8 -*-
# pylint:disable=invalid-name, logging-format-interpolation
"""Featurization functions for the oxidation state mining project. Wrapper around matminer"""
from __future__ import absolute_import
from pathlib import Path
import os
import pickle
import logging
import warnings
from collections import defaultdict
from ase.io import read
from pymatgen.io.ase import AseAtomsAdaptor
from matminer.featurizers.base import MultipleFeaturizer
from matminer.featurizers.site import (CrystalNNFingerprint, CoordinationNumber, LocalPropertyDifference,
                                       BondOrientationalParameter, GaussianSymmFunc)


class GetFeatures():
    """Featurizer"""

    def __init__(self, structure, outpath):
        """Generates features for a list of structures

        Args:
            structure_paths (str): path to structure
            outpath (str): path to which the features will be dumped

        Returns:

        """
        self.outpath = outpath
        logging.basicConfig(filename=os.path.join(self.outpath, 'log'),
                            level=logging.DEBUG,
                            format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
                            datefmt='%H:%M:%S')
        self.logger = logging.getLogger(__name__)
        self.path = structure
        self.structure = None
        self.metal_sites = []
        self.metal_indices = []
        self.features = defaultdict(dict)
        self.outname = os.path.join(self.outpath, ''.join([Path(structure).stem, '.pkl']))

    def precheck(self):
        """Fail early

        Returns:
            bool: True if check ok (if pymatgen can load structure)

        """
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            try:
                atoms = read(self.path)
                self.structure = AseAtomsAdaptor.get_structure(atoms)
                return True
            except Exception:  # pylint: disable=broad-except
                return False

    def get_metal_sites(self):
        """Stores all metal sites of structure  to list"""
        for idx, site in enumerate(self.structure):
            if site.species.elements[0].is_metal:
                self.metal_sites.append(site)
                self.metal_indices.append(idx)

    def get_feature_vectors(self, site):
        """Runs matminer on one site"""
        featurizer = MultipleFeaturizer([
            CrystalNNFingerprint.from_preset('ops'),
            CoordinationNumber(),
            LocalPropertyDifference(),
            BondOrientationalParameter(),
            GaussianSymmFunc()
        ])

        X = featurizer.featurize(self.structure, site)
        return X

    def dump_features(self):
        """Dumps all the features into one pickle file"""
        with open(self.outname, 'wb') as filehandle:
            pickle.dump(dict(self.features), filehandle)

    def run_featurization(self):
        """loops over sites if check ok"""
        if self.precheck():
            self.get_metal_sites()
            try:
                for idx, metal_site in enumerate(self.metal_sites):
                    self.features[metal_site.species_string]['feature'] = self.get_feature_vectors(
                        self.metal_indices[idx])
                    self.features[metal_site.species_string]['coords'] = metal_site.coords
                self.dump_features()
            except Exception:  # pylint: disable=broad-except
                self.logger.error('could not featurize {}'.format(self.path))
        else:
            self.logger.error('could not load {}'.format(self.path))
