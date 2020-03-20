"""
Live test suite for askcos web api

This will test api functionality for a live instance of the askcos site
"""

import unittest

from requests import Session


class TestAPI(unittest.TestCase):
    """Test class for askcos api v2"""

    @classmethod
    def setUpClass(cls):
        """This method is run once before all tests in this class."""
        cls.client = Session()
        cls.client.verify = False

    def test_buyables(self):
        """Test /buyables endpoint"""
        # Get request for main endpoint
        response = self.client.get('https://localhost/api/v2/buyables/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(len(result['result']), 100)  # returns 100 results by default

        # Post request to add buyable
        data = {
            'smiles': 'C1CCC1',
            'ppg': '2.0',
            'allowOverwrite': False,
        }
        response = self.client.post('https://localhost/api/v2/buyables/', data=data)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])
        _id = result['inserted']['_id']

        # Post request to upload buyables (both are duplicates)
        filedata = '[{"smiles": "C1CCC1","ppg": "2.0"},{"smiles": "C1CCCC1","ppg": "3.0"}]'
        files = {'file': ('upload.json', filedata)}
        data = {'format': 'json', 'allowOverwrite': False}
        response = self.client.post('https://localhost/api/v2/buyables/upload/', data=data, files=files)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])
        self.assertEqual(result['inserted'], [])
        self.assertEqual(result['updated'], [])
        self.assertEqual(result['duplicate_count'], 2)
        self.assertEqual(result['total'], 2)

        # Get request with query
        response = self.client.get('https://localhost/api/v2/buyables/?q=C1CCC1')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(len(result['result']), 1)
        self.assertEqual(result['result'][0]['smiles'], 'C1CCC1')

        # Get request for specific buyable
        response = self.client.get('https://localhost/api/v2/buyables/{0}/'.format(_id))
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(len(result['result']), 1)
        self.assertEqual(result['result'][0]['smiles'], 'C1CCC1')

        # Delete request for specific buyable
        response = self.client.delete('https://localhost/api/v2/buyables/{0}/'.format(_id))
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_celery_status(self):
        """Test /celery endpoint"""
        response = self.client.get('https://localhost/api/v2/celery/')
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertIsInstance(result['queues'], list)

    def test_celery_task_status(self):
        """Test /celery/task endpoint"""
        response = self.client.get('https://localhost/api/v2/celery/task/abc/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'complete': False})

    def test_cluster(self):
        """Test /cluster endpoint"""
        data = {
            'original': 'CN(C)CCOC(c1ccccc1)c1ccccc1',
            'outcomes': ['OC(c1ccccc1)c1ccccc1.CN(C)CCCl',
                         'ClC(c1ccccc1)c1ccccc1.CN(C)CCO',
                         'O=C(c1ccccc1)c1ccccc1.CN(C)CCO']
        }
        response = self.client.post('https://localhost/api/v2/cluster/', data=data)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['request']['original'], data['original'])
        self.assertEqual(result['request']['outcomes'], data['outcomes'])

        self.assertIsInstance(result['output'], list)
        self.assertEqual(result['output'], [0, 0, 1])

        response = self.client.post('https://localhost/api/v2/cluster/', data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'original': ['This field is required.'],
                                           'outcomes': ['This field is required.']})

    def test_context(self):
        """Test /context endpoint"""
        data = {
            'reactants': 'CN(C)CCCl.OC(c1ccccc1)c1ccccc1',
            'products': 'CN(C)CCOC(c1ccccc1)c1ccccc1',
            'num_results': 5,
            'return_scores': True,
            'async': False
        }
        response = self.client.post('https://localhost/api/v2/context/', data=data)
        self.assertEqual(response.status_code, 200)

        # Confirm that request was interpreted correctly
        result = response.json()
        request = result['request']
        self.assertEqual(request['reactants'], data['reactants'])
        self.assertEqual(request['products'], data['products'])
        self.assertEqual(request['num_results'], data['num_results'])
        self.assertTrue(request['return_scores'])

        self.assertEqual(len(result['output']), 5)
        o = result['output'][0]
        self.assertEqual(o['catalyst'], '')
        self.assertEqual(o['reagent'], 'Cc1ccccc1.[H][N-][H].[Na+]')
        self.assertAlmostEqual(o['score'], 0.339, places=2)
        self.assertEqual(o['solvent'], '')
        self.assertAlmostEqual(o['temperature'], 94.48, places=1)

        # Test insufficient data
        response = self.client.post('https://localhost/api/v2/context/', data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'reactants': ['This field is required.'],
                                           'products': ['This field is required.']})

        # Test unparseable smiles
        response = self.client.post('https://localhost/api/v2/context/', data={'reactants': 'X', 'products': 'X'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'reactants': ['Cannot parse reactants smiles with rdkit.'],
                                           'products': ['Cannot parse products smiles with rdkit.']})

    def test_fast_filter(self):
        """Test /fast-filter endpoint"""
        data = {
            'reactants': 'CN(C)CCCl.OC(c1ccccc1)c1ccccc1',
            'products': 'CN(C)CCOC(c1ccccc1)c1ccccc1',
        }
        response = self.client.post('https://localhost/api/v2/fast-filter/', data=data)
        self.assertEqual(response.status_code, 200)

        # Confirm that request was interpreted correctly
        result = response.json()
        request = result['request']
        self.assertEqual(request['reactants'], data['reactants'])
        self.assertEqual(request['products'], data['products'])

        # Check result
        self.assertAlmostEqual(result['output'], 0.998, places=2)

        # Test insufficient data
        response = self.client.post('https://localhost/api/v2/fast-filter/', data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'reactants': ['This field is required.'],
                                           'products': ['This field is required.']})

        # Test unparseable smiles
        response = self.client.post('https://localhost/api/v2/fast-filter/', data={'reactants': 'X', 'products': 'X'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'reactants': ['Cannot parse reactants smiles with rdkit.'],
                                           'products': ['Cannot parse products smiles with rdkit.']})

    def test_forward(self):
        """Test /forward endpoint"""
        data = {
            'reactants': 'CN(C)CCCl.OC(c1ccccc1)c1ccccc1',
            'num_results': 5,
            'async': False,
        }
        response = self.client.post('https://localhost/api/v2/forward/', data=data)
        self.assertEqual(response.status_code, 200)

        # Confirm that request was interpreted correctly
        result = response.json()
        request = result['request']
        self.assertEqual(request['reactants'], data['reactants'])
        self.assertEqual(request['reagents'], '')
        self.assertEqual(request['solvent'], '')
        self.assertEqual(request['num_results'], data['num_results'])

        self.assertEqual(len(result['output']), 5)
        o = result['output'][0]
        self.assertEqual(o['smiles'], 'CN(C)CCOC(c1ccccc1)c1ccccc1')
        self.assertAlmostEqual(o['mol_wt'], 255.36, places=2)
        self.assertEqual(o['rank'], 1)
        self.assertAlmostEqual(o['score'], -63.3, places=1)
        self.assertAlmostEqual(o['prob'], 0.91, places=2)

        # Test insufficient data
        response = self.client.post('https://localhost/api/v2/forward/', data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'reactants': ['This field is required.']})

        # Test unparseable smiles
        response = self.client.post('https://localhost/api/v2/forward/', data={'reactants': 'X'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'reactants': ['Cannot parse reactants smiles with rdkit.']})

    def test_impurity(self):
        """Test /impurity endpoint"""
        data = {
            'reactants': 'CN(C)CCCl.OC(c1ccccc1)c1ccccc1',
            'async': True,
        }
        response = self.client.post('https://localhost/api/v2/impurity/', data=data)
        self.assertEqual(response.status_code, 200)

        # Confirm that request was interpreted correctly
        result = response.json()
        request = result['request']
        self.assertEqual(request['reactants'], data['reactants'])
        self.assertEqual(request['reagents'], '')
        self.assertEqual(request['products'], '')
        self.assertEqual(request['solvent'], '')
        self.assertEqual(request['top_k'], 3)
        self.assertEqual(request['threshold'], 0.75)
        self.assertEqual(request['predictor'], 'WLN forward predictor')
        self.assertEqual(request['inspector'], 'Reaxys predictor')
        self.assertEqual(request['mapper'], 'WLN atom mapper')
        self.assertTrue(request['check_mapping'])

        self.assertIsNotNone(result['task_id'])

        # Test insufficient data
        response = self.client.post('https://localhost/api/v2/impurity/', data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'reactants': ['This field is required.']})

        # Test unparseable smiles
        response = self.client.post('https://localhost/api/v2/impurity/', data={'reactants': 'X'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'reactants': ['Cannot parse smiles with rdkit.']})

    def test_reactions(self):
        """Test /reactions endpoint"""
        data = {
            'ids': ['1'],
        }
        response = self.client.post('https://localhost/api/v2/reactions/', data=data)
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertEqual(result['reactions'], [])

        # Test insufficient data
        response = self.client.post('https://localhost/api/v2/reactions/', data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'ids': ['This field is required.']})

    def test_rdkit_smiles(self):
        """Test /rdkit/smiles endpoints"""
        data = {
            'smiles': 'c1ccccc1C(OCCN(C)C)c1ccccc1',
        }

        # Test canonicalization
        response = self.client.post('https://localhost/api/v2/rdkit/smiles/canonicalize/', data=data)
        self.assertEqual(response.status_code, 200)

        # Check that we got expected result
        self.assertEqual(response.json(), {'smiles': 'CN(C)CCOC(c1ccccc1)c1ccccc1'})

        # Test insufficient data
        response = self.client.post('https://localhost/api/v2/rdkit/smiles/canonicalize/', data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'smiles': ['This field is required.']})

        # Test validation
        response = self.client.post('https://localhost/api/v2/rdkit/smiles/validate/', data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'correct_syntax': True, 'valid_chem_name': True})

        molfile = {
            'molfile': """
     RDKit          2D

 19 20  0  0  0  0  0  0  0  0999 V2000
    1.5000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.7500   -1.2990    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.7500   -1.2990    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -1.5000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.7500    1.2990    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.7500    1.2990    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.5000    2.5981    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.7500    3.8971    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    1.5000    5.1962    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.7500    6.4952    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.5000    7.7942    0.0000 N   0  0  0  0  0  0  0  0  0  0  0  0
    0.7500    9.0933    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    3.0000    7.7942    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    3.0000    2.5981    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    3.7500    1.2990    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    5.2500    1.2990    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    6.0000    2.5981    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    5.2500    3.8971    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    3.7500    3.8971    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  2  0
  2  3  1  0
  3  4  2  0
  4  5  1  0
  5  6  2  0
  6  7  1  0
  7  8  1  0
  8  9  1  0
  9 10  1  0
 10 11  1  0
 11 12  1  0
 11 13  1  0
  7 14  1  0
 14 15  2  0
 15 16  1  0
 16 17  2  0
 17 18  1  0
 18 19  2  0
  6  1  1  0
 19 14  1  0
M  END
""",
        }

        # Test molfile generation
        response = self.client.post('https://localhost/api/v2/rdkit/smiles/to_molfile/', data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), molfile)

        # Test molfile parsing
        response = self.client.post('https://localhost/api/v2/rdkit/smiles/from_molfile/', data=molfile)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'smiles': 'CN(C)CCOC(c1ccccc1)c1ccccc1'})

    @unittest.skip('Requires login credentials.')
    def test_results(self):
        """Test /results endpoint and token authentication"""
        # Test that access is denied without authentication
        response = self.client.get('https://localhost/api/v2/results/')
        self.assertEqual(response.status_code, 401)

        # Test that we can get a token (need to provide valid credentials, even for testing)
        data = {
            'username': '',
            'password': '',
        }
        response = self.client.post('https://localhost/api/v2/token-auth/', data=data)
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertIn('token', result)
        token = result['token']

        # Test that we can access using the token
        headers = {
            'Authorization': 'Bearer {0}'.format(token),
        }
        response = self.client.get('https://localhost/api/v2/results/', headers=headers)
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertIsInstance(result['results'], list)
        result_id = result['results'][0]['id']

        # Test checking the status of a result
        response = self.client.get('https://localhost/api/v2/results/{0}/check'.format(result_id), headers=headers)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['id'], result_id)
        self.assertEqual(result['state'], 'completed')
        self.assertIsNone(result['error'])

        # Test retrieving a result
        response = self.client.get('https://localhost/api/v2/results/{0}/'.format(result_id), headers=headers)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['id'], result_id)
        self.assertIsInstance(result['result'], dict)
        self.assertIsNone(result['error'])

        # Test deleting a non-existent result
        response = self.client.delete('https://localhost/api/v2/results/{0}/'.format('random'), headers=headers)
        self.assertEqual(response.status_code, 404)
        result = response.json()
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Result not found!')

    def test_retro(self):
        """Test /retro endpoint"""
        data = {
            'target': 'CN(C)CCOC(c1ccccc1)c1ccccc1',
            'async': False,
        }
        response = self.client.post('https://localhost/api/v2/retro/', data=data)
        self.assertEqual(response.status_code, 200)

        # Confirm that request was interpreted correctly
        result = response.json()
        request = result['request']
        self.assertEqual(request['target'], data['target'])
        self.assertEqual(request['num_templates'], 100)
        self.assertEqual(request['max_cum_prob'], 0.995)
        self.assertEqual(request['filter_threshold'], 0.75)
        self.assertEqual(request['template_set'], 'reaxys')
        self.assertEqual(request['template_prioritizer'], 'reaxys')
        self.assertTrue(request['cluster'])
        self.assertEqual(request['cluster_method'], 'kmeans')
        self.assertEqual(request['cluster_feature'], 'original')
        self.assertEqual(request['cluster_fp_type'], 'morgan')
        self.assertEqual(request['cluster_fp_length'], 512)
        self.assertEqual(request['cluster_fp_radius'], 1)

        self.assertIsInstance(result['output'], list)

        # Test insufficient data
        response = self.client.post('https://localhost/api/v2/retro/', data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'target': ['This field is required.']})

        # Test unparseable smiles
        response = self.client.post('https://localhost/api/v2/retro/', data={'target': 'X'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'target': ['Cannot parse target smiles with rdkit.']})

    def test_scscore(self):
        """Test /scscore endpoint"""
        data = {
            'smiles': 'CN(C)CCOC(c1ccccc1)c1ccccc1',
        }
        response = self.client.post('https://localhost/api/v2/scscore/', data=data)
        self.assertEqual(response.status_code, 200)

        # Confirm that request was interpreted correctly
        result = response.json()
        request = result['request']
        self.assertEqual(request['smiles'], data['smiles'])

        # Check that we got expected result
        self.assertAlmostEqual(result['score'], 2.159, places=3)

        # Test insufficient data
        response = self.client.post('https://localhost/api/v2/scscore/', data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'smiles': ['This field is required.']})

        # Test unparseable smiles
        response = self.client.post('https://localhost/api/v2/scscore/', data={'smiles': 'X'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'smiles': ['Cannot parse smiles with rdkit.']})

    def test_selectivity(self):
        """Test /selectivity endpoint"""
        data = {
            'smiles': 'Cc1ccccc1',
            'async': False,
        }
        response = self.client.post('https://localhost/api/v2/selectivity/', data=data)
        self.assertEqual(response.status_code, 200)

        # Confirm that request was interpreted correctly
        result = response.json()
        request = result['request']
        self.assertEqual(request['smiles'], data['smiles'])

        # Check that we got expected result
        self.assertIsInstance(result['output'], list)
        self.assertEqual(len(result['output']), 123)

        # Test insufficient data
        response = self.client.post('https://localhost/api/v2/selectivity/', data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'smiles': ['This field is required.']})

        # Test unparseable smiles
        response = self.client.post('https://localhost/api/v2/selectivity/', data={'smiles': 'X'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'smiles': ['Cannot parse smiles with rdkit.']})

    def test_template(self):
        """Test /template endpoint"""
        # Get request for specific template endpoint
        template_id = '5e1f4b6f63488328509a594e'
        response = self.client.get('https://localhost/api/v2/template/{0}/'.format(template_id))
        self.assertEqual(response.status_code, 200)

        # Check retrieved template
        result = response.json()
        template = result['template']
        self.assertIsNotNone(template)
        self.assertEqual(template['template_set'], 'reaxys')
        self.assertEqual(template['_id'], template_id)
        self.assertEqual(template['references'], ['100336', '100337', '555364', '3948785', '3948834',
                                                  '28127174', '35585623', '38022824', '38022828',
                                                  '38022830', '38022834', '38022833', '38022835',
                                                  '38022845', '41610599', '41610601', '41610620'])

        # Get request for specific template reaxys query export endpoint
        response = self.client.get('https://localhost/api/v2/template/{0}/export'.format(template_id))
        self.assertEqual(response.status_code, 200)

        # Check exported json
        result = response.json()
        self.assertEqual(result['fileName'], 'reaxys_query.json')
        self.assertEqual(len(result['content']['facts']), 1)
        fact = result['content']['facts'][0]
        self.assertEqual(fact['id'], 'Reaxys487')
        self.assertEqual(len(fact['fields']), 1)
        field = fact['fields'][0]
        self.assertEqual(field['id'], 'RX.ID')
        self.assertEqual(field['displayName'], 'Reaction ID')
        self.assertEqual(field['boundOperator'], 'op_num_equal')
        self.assertEqual(field['value'],
                         '100336; 100337; 555364; 3948785; 3948834; 28127174; 35585623; 38022824; 38022828; 38022830; 38022834; 38022833; 38022835; 38022845; 41610599; 41610601; 41610620')

    def test_tree_builder(self):
        """Test /treebuilder endpoint"""
        data = {
            'smiles': 'CN(C)CCOC(c1ccccc1)c1ccccc1',
            'async': False,
            'return_first': True,
        }
        response = self.client.post('https://localhost/api/v2/treebuilder/', data=data)
        self.assertEqual(response.status_code, 200)

        # Confirm that request was interpreted correctly
        result = response.json()
        request = result['request']
        self.assertEqual(request['smiles'], data['smiles'])
        self.assertEqual(request['async'], False)
        self.assertEqual(request['return_first'], True)
        self.assertEqual(request['chemical_property_logic'], 'none')
        self.assertEqual(request['chemical_popularity_logic'], 'none')
        self.assertEqual(request['template_set'], 'reaxys')
        self.assertEqual(request['template_prioritizer'], 'reaxys')

        # Check that we got a result (can't check values because it's non-deterministic)
        self.assertIsInstance(result['output'], list)
        self.assertIsInstance(result['output'][0], dict)
        self.assertIsInstance(result['output'][0]['children'], list)

        # Test insufficient data
        response = self.client.post('https://localhost/api/v2/treebuilder/', data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'smiles': ['This field is required.']})

        # Test unparseable smiles
        response = self.client.post('https://localhost/api/v2/treebuilder/', data={'smiles': 'X'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'smiles': ['Cannot parse smiles with rdkit.']})

    @classmethod
    def tearDownClass(cls):
        """This method is run once after all tests in this class."""
        cls.client.close()


if __name__ == '__main__':
    res = unittest.main(verbosity=3, exit=False)
