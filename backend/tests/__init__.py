"""
Test suite for the Polymer Analysis Toolkit.

The tests are organised by what they protect:

* ``test_molar_mass.py``      - the averages and their analytic identities
* ``test_ingest.py``          - every real-world file convention
* ``test_api_molecular.py``   - the HTTP contract, including the two bugs that
                                made the previous release unusable
* ``test_thermal.py``         - TGA and DSC against synthetic traces with
                                known answers
* ``test_characterization.py`` - tensile, rheology, XRD, FTIR
"""
