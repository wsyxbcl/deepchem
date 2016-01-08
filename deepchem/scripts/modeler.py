"""
Top level script to featurize input, train models, and evaluate them.
"""
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
import argparse
import os
from deepchem.utils.featurize import featurize_inputs
from deepchem.utils.evaluate import eval_trained_model
from deepchem.utils.preprocess import train_test_split
from deepchem.utils.fit import fit_model

def add_featurization_command(subparsers):
  """Adds flags for featurize subcommand."""
  featurize_cmd = subparsers.add_parser(
      "featurize", help="Featurize raw input data.")
  add_featurize_group(featurize_cmd)

def add_featurize_group(featurize_cmd):
  """Adds flags for featurizization."""
  featurize_group = featurize_cmd.add_argument_group("Input Specifications")
  featurize_group.add_argument(
      "--input-files", required=1, nargs="+",
      help="Input file with data.")
  featurize_group.add_argument(
      "--user-specified-features", type=str, nargs="+",
      help="Optional field that holds pre-computed feature vector")
  featurize_group.add_argument(
      "--tasks", type=str, nargs="+", required=1,
      help="Name of measured field to predict.")
  featurize_group.add_argument(
      "--split-field", type=str, default=None,
      help="Name of field specifying train/test split.")
  featurize_group.add_argument(
      "--smiles-field", type=str, default="smiles",
      help="Name of field specifying SMILES for molecule.")
  featurize_group.add_argument(
      "--id-field", type=str, default=None,
      help="Name of field specifying unique identifier for molecule.\n"
           "If none is specified, then smiles-field is used as identifier.")
  featurize_group.add_argument(
      "--threshold", type=float, default=None,
      help="If specified, will be used to binarize real-valued target-fields.")
  featurize_group.add_argument(
      "--feature-dir", type=str, required=0,
      help="Directory where featurized dataset will be stored.\n"
           "Will be created if does not exist")
  featurize_group.set_defaults(func=featurize_inputs_wrapper)

def add_transforms_group(cmd):
  """Adds flags for data transforms."""
  transform_group = cmd.add_argument_group("Transform Group")
  transform_group.add_argument(
      "--input-transforms", nargs="+", default=[],
      choices=["normalize", "truncate", "log"],
      help="Transforms to apply to input data.")
  transform_group.add_argument(
      "--output-transforms", nargs="+", default=[],
      choices=["normalize", "log"],
      help="Supported transforms are 'log' and 'normalize'. 'None' will be taken\n"
           "to mean no transforms are required.")
  transform_group.add_argument(
      "--mode", default="singletask",
      choices=["singletask", "multitask"],
      help="Type of model being built.")
  transform_group.add_argument(
      "--feature-types", nargs="+", required=1,
      choices=["user-specified-features", "ECFP", "RDKIT-descriptors"],
      help="Featurizations of data to use.\n"
           "'features' denotes user-defined features.\n"
           "'fingerprints' denotes ECFP fingeprints.\n"
           "'descriptors' denotes RDKit chem descriptors.\n")
  transform_group.add_argument(
      "--splittype", type=str, default="scaffold",
      choices=["scaffold", "random", "specified"],
      help="Type of train/test data-split. 'scaffold' uses Bemis-Murcko scaffolds.\n"
           "specified requires that split be in original data.")
  transform_group.add_argument(
      "--weight-positives", type=bool, default=False,
      help="Weight positive examples to have same total weight as negatives.")

def add_train_test_command(subparsers):
  """Adds flags for train-test-split subcommand."""
  train_test_cmd = subparsers.add_parser(
      "train-test-split",
      help="Apply standard data transforms to raw features generated by featurize,\n"
           "then split data into train/test and store data as (X,y) matrices.")
  add_transforms_group(train_test_cmd)
  train_test_cmd.add_argument(
      "--paths", nargs="+", required=1,
      help="Paths to input datasets.")
  train_test_cmd.add_argument(
      "--data-dir", type=str, required=1,
      help="Location to save train and test data.")
  train_test_cmd.set_defaults(func=train_test_split_wrapper)

def add_model_group(fit_cmd):
  """Adds flags for specifying models."""
  group = fit_cmd.add_argument_group("model")
  group.add_argument(
      "--model", required=1,
      choices=["logistic", "rf_classifier", "rf_regressor",
               "linear", "ridge", "lasso", "lasso_lars", "elastic_net",
               "singletask_deep_classifier", "multitask_deep_classifier",
               "singletask_deep_regressor", "multitask_deep_regressor",
               "convolutional_3D_regressor"],
      help="Type of model to build. Some models may allow for\n"
           "further specification of hyperparameters. See flags below.")

  group = fit_cmd.add_argument_group("Neural Net Parameters")
  group.add_argument(
      "--nb-hidden", type=int, default=500,
      help="Number of hidden neurons for NN models.")
  group.add_argument(
      "--learning-rate", type=float, default=0.01,
      help="Learning rate for NN models.")
  group.add_argument(
      "--dropout", type=float, default=0.5,
      help="Learning rate for NN models.")
  group.add_argument(
      "--nb-epoch", type=int, default=50,
      help="Number of epochs for NN models.")
  group.add_argument(
      "--batch-size", type=int, default=32,
      help="Number of examples per minibatch for NN models.")
  group.add_argument(
      "--loss-function", type=str, default="mean_squared_error",
      help="Loss function type.")
  group.add_argument(
      "--decay", type=float, default=1e-4,
      help="Learning rate decay for NN models.")
  group.add_argument(
      "--activation", type=str, default="relu",
      help="NN activation function.")
  group.add_argument(
      "--momentum", type=float, default=.9,
      help="Momentum for stochastic gradient descent.")
  group.add_argument(
      "--nesterov", action="store_true",
      help="If set, use Nesterov acceleration.")

def add_fit_command(subparsers):
  """Adds arguments for fit subcommand."""
  fit_cmd = subparsers.add_parser(
      "fit", help="Fit a model to training data.")
  group = fit_cmd.add_argument_group("load-and-transform")
  group.add_argument(
      "--data-dir", required=1,
      help="Location of saved transformed data.")
  add_model_group(fit_cmd)
  group = fit_cmd.add_argument_group("save")
  group.add_argument(
      "--model-dir", type=str, required=1,
      help="Location to save trained model.")
  fit_cmd.set_defaults(func=fit_model_wrapper)

def add_eval_command(subparsers):
  """Adds arguments for eval subcommand."""
  eval_cmd = subparsers.add_parser(
      "eval",
      help="Evaluate trained model on test data processed by transform.")
  group = eval_cmd.add_argument_group("load model/data")
  group.add_argument(
      "--saved-model", type=str, required=1,
      help="Location from which to load saved model.")
  group.add_argument(
      "--saved-data", required=1, help="Location of saved transformed data.")
  eval_cmd.add_argument(
      "--csv-out", type=str, required=1,
      help="Outputted predictions on evaluated set.")
  eval_cmd.add_argument(
      "--stats-out", type=str, required=1j,
      help="Computed statistics on evaluated set.")
  eval_cmd.set_defaults(func=eval_trained_model_wrapper)

def add_predict_command(subparsers):
  """Adds arguments for predict subcommand."""
  predict_cmd = subparsers.add_parser(
    "predict",
    help="Make predictions of model on new data.")
  #group = predict_cmd.add_a

# TODO(rbharath): There are a lot of duplicate commands introduced here. Is
# there a nice way to factor them?
def add_model_command(subparsers):
  """Adds flags for model subcommand."""
  model_cmd = subparsers.add_parser(
      "model", help="Combines featurize, train-test-split, fit, eval into one\n"
      "command for user convenience.")
  model_cmd.add_argument(
      "--skip-featurization", action="store_true",
      help="If set, skip the featurization step.")
  model_cmd.add_argument(
      "--skip-train-test-split", action="store_true",
      help="If set, skip the train-test-split step.")
  model_cmd.add_argument(
      "--skip-fit", action="store_true",
      help="If set, skip model fit step.")
  model_cmd.add_argument(
      "--skip-eval", action="store_true",
      help="If set, skip model eval step.")
  model_cmd.add_argument(
      "--base-dir", type=str, required=1,
      help="The base directory for the model.")
  add_featurize_group(model_cmd)

  add_transforms_group(model_cmd)
  add_model_group(model_cmd)
  model_cmd.set_defaults(func=create_model)

def extract_model_params(args):
  """
  Given input arguments, return a dict specifiying model parameters.
  """
  params = ["nb_hidden", "learning_rate", "dropout",
            "nb_epoch", "decay", "batch_size", "loss_function",
            "activation", "momentum", "nesterov"]

  model_params = {param : getattr(args, param) for param in params}
  return(model_params)

def ensure_exists(dirs):
  for directory in dirs:
    if not os.path.exists(directory):
      os.makedirs(directory)

def create_model(args):
  """Creates a model"""
  base_dir = args.base_dir
  feature_dir = os.path.join(base_dir, "features")
  data_dir = os.path.join(base_dir, "data")
  model_dir = os.path.join(base_dir, "model")
  ensure_exists([base_dir, feature_dir, data_dir, model_dir])

  model_name = args.model

  print("+++++++++++++++++++++++++++++++++")
  print("Perform featurization")
  if not args.skip_featurization:
    featurize_inputs(
        feature_dir, args.input_files,
        args.user_specified_features, args.tasks,
        args.smiles_field, args.split_field, args.id_field, args.threshold)

  print("+++++++++++++++++++++++++++++++++")
  print("Perform train-test split")
  paths = [feature_dir]
  if not args.skip_train_test_split:
    train_test_split(
        paths, args.input_transforms, args.output_transforms, args.feature_types,
        args.splittype, args.mode, data_dir)

  print("+++++++++++++++++++++++++++++++++")
  print("Fit model")
  if not args.skip_fit:
    model_params = extract_model_params(args)
    fit_model(
        model_name, model_params, model_dir, data_dir)

  print("+++++++++++++++++++++++++++++++++")
  print("Eval Model on Train")
  print("-------------------")
  if not args.skip_fit:
    csv_out_train = os.path.join(data_dir, "train.csv")
    stats_out_train = os.path.join(data_dir, "train-stats.txt")
    csv_out_test = os.path.join(data_dir, "test.csv")
    stats_out_test = os.path.join(data_dir, "test-stats.txt")
    train_dir = os.path.join(data_dir, "train")
    eval_trained_model(
        model_name, model_dir, train_dir, csv_out_train,
        stats_out_train, args.output_transforms, split="train")
  print("Eval Model on Test")
  print("------------------")
  if not args.skip_fit:
    test_dir = os.path.join(data_dir, "test")
    eval_trained_model(
        model_name, model_dir, test_dir, csv_out_test,
        stats_out_test, args.output_transforms, split="test")

def parse_args(input_args=None):
  """Parse command-line arguments."""
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(title='Modes')

  add_featurization_command(subparsers)
  add_train_test_command(subparsers)
  add_fit_command(subparsers)
  add_eval_command(subparsers)

  add_model_command(subparsers)

  return parser.parse_args(input_args)

def featurize_inputs_wrapper(args):
  """Wrapper function that calls _featurize_input with args unwrapped."""
  if not os.path.exists(args.feature_dir):
    os.makedirs(args.feature_dir)
  featurize_inputs(
      args.feature_dir, args.input_files, args.user_specified_features,
      args.tasks, args.smiles_field, args.split_field, args.id_field,
      args.threshold)

def train_test_split_wrapper(args):
  """Wrapper function that calls _train_test_split_wrapper after unwrapping args."""
  train_test_split(args.paths, args.input_transforms, 
                   args.output_transforms, args.feature_types,
                   args.splittype, args.mode, args.data_dir)

def fit_model_wrapper(args):
  """Wrapper that calls _fit_model with arguments unwrapped."""
  model_params = extract_model_params(args)
  fit_model(
      args.model_name, model_params, args.model_dir, args.data_dir)

def eval_trained_model_wrapper(args):
  """Wrapper function that calls _eval_trained_model with unwrapped args."""
  eval_trained_model(
      args.model, args.model_dir, args.data_dir,
      args.csv_out, args.stats_out, args.output_transforms, split="test")

def main():
  """Invokes argument parser."""
  args = parse_args()
  args.func(args)

if __name__ == "__main__":
  main()
