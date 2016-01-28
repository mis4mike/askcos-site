# Make-It (makeit)
### Description
Prediction of chemical reactivity

### Requirements
The following is a list of non-default python packages known to be required by makeit:
- numpy
- cython
- pyplot
- graphviz
- Theano
- keras
- cpickle
- h5py

For creating new datasets from the Mongo database (Bishop's data), the following are also required:
- rdkit
- pymongo
- cirpy (currently unused)

Most of these can each be installed through
<code>pip install [package name]</code>. The OPSIN chemical name resolver, which is currently unused, requires Java to run.

### Workflow
#### 1. Prepare data sets
To avoid interacting with the database directly, any information relevant for a certain task should be pre-parsed and resaved as a .json dump. This is done by running <code>python makeit/utils/generate_data_subsets.py "data type" [max # records]</code> with the appropriate arguments. Currently, there are three available types of data:

- <code>"chemical_names_with_mws"</code> : each element in the dumped list consists of <code>[str(name), float(mol_weight)]</code>, for chemicals with non-empty names and non-empty molecular weights.
- <code>"reactions_2reac_1prod"</code> : each element in the dumped list consists of <code>[str(A_name), str(B_name), str(C_name), float(yield)]</code>, for reactions with exactly two reactants and one product and non-empty chemical names for each.
- <code>"reactions_2reac_rdsmiles"</code> : each element in the dumped list consists of <code>[str(A_smiles), str(B_smiles), float(yield)]</code>, for reactions with exactly two reactants, reactants with valid SMILES strings that can be parsed by RDKit, and yield not equal to 0.75.
- <code>"reactions_2reac_smilesyield"</code> : each element in the dumped list consists of <code>[str(reaction_smiles), float(yield)]</code>, for reactions with non-empty smiles strings and yields not equal to 0.75. There are about 179,000 reactions in this dataset.
- <code>"all_reaction_dois"</code> : each element in the dumped list consists of <code>str(doi)</code> for whatever DOIs can be found in the reaction database for any set of references within any reaction document.
- <code>"chemical_names"</code> : each element in the dumped list consists of <code>str(name)</code>, wherever the name field is not empty.
- <code>"chemical_rdsmiles"</code> : each element in the dumped list consists of <code>str(smiles)</code>, where each SMILES string can be parsed by RDKit uniquely.

#### 2. Build tokenizer
The tokenizer must be fit before it can be used, so that words can be scored and ranked by the frequency of their occurrence in the corpus. 

###### Chemical names
For speed, building the tokenizer requires a json file which consists of a list of chemical names. This can be generated using the <code>"chemical_names"</code> option in <code>generate_data_subsets.py</code>. 

Chemical name tokenizers can be generated by running <code>python makeit/main/tokenize_chemicals.py "data_file.json" [max # vocab]</code>. It should not be necessary to run this script very often. The fitted tokenizer is saved using <code>cPickle</code>.

###### SMILES strings
For speed, building the tokenizer requires a json file which consists of a list of reaction smiles strings as its first element. This can be generated using the <code>"reactions_2reac_smilesyield"</code> otpion in <code>generate_data_subsets.py</code>

The SMILES reaction tokenzier can be generated by running <code>python makeit/main/tokenize_rxnsmiles.py "data_file.json" [max # vocab]</code>. It should not be necessary to run this script very often. The fitted tokenizer is saved as a dictionary using <code>json</code>, where each key is a character and each value is an index inversely related to its frequency in the corpus.

#### 3. Run models (ongoing)
For each different model (e.g., different model structure, sets of inputs, sets of outputs), there should be a different python file. There is currently one model type that uses the most up-to-date input structure, <code>neural_smiles_to_yield.py</code>. This file is run as <code>python neural_smiles_to_yield.py "config_file.cfg"</code>. When running on a GPU cluster (e.g., rosetta3 on CSAIL), this command should be prepended with <code>THEANO_FLAGS=device=gpu,floatX=float32</code>. An example of the input file is shown below:

```python
[IO]
model_fpath: makeit/models/neural_smiles_to_yield_01_27_2016_nodrouput_adamopt
tokenizer_fpath: makeit/models/tokenizer_rxnsmiles.json
data_fpath: makeit/data/reactions_2reac_smilesyield_179013.json

[ARCHITECTURE]
use_existing: true
embedding_size: 100
lstm_size: 100
optimizer: adam
lr: 0.01

[TRAINING]
use_existing: true
truncate_to: 50000
batch_size: 600
nb_epoch: 10
```

If a model has been built and saved before, then ARCHITECTURE/use_existing will load the model from a .json file instead of re-building and re-compiling according to the specified layer sizes, optimizer, and learning rate. Similarly, weights can be loaded using TRAINING/use_existing. An error will be thrown if you attempt to use_existing when there is no such file to load from. Note that if you want to re-train an existing model using a different learning rate, it is necessary to re-build that model and set ARCHITECTURE/use_existing to false.

After training, the model is evaluated numerically for the test set using the loss function (mean-squared error, in this case). Parity plots are also generated for both the training and testing datasets and saved with a timestamp. In this manner, progress in prediction accuracy can be visualized over time.
