# Train ACE event extraction model.
# Usage: bash scripts/train/train_ace05_event.sh [gpu-id]
# gpu-id can be an integer GPU ID, or -1 for CPU.

experiment_name="clinical-trials-gov-event"
data_root="./data/preprocessed/ner"
json_dir=$data_root/json
config_file="./src/ner/dygie/training_config/clinical_trials_gov_event.jsonnet"
models_dir=$data_root/models
cuda_device=-1

rm -rf $models_dir/$experiment_name

# Train model.
ie_train_data_path=$json_dir/train.json              \
    ie_dev_data_path=$json_dir/dev.json              \
    ie_test_data_path=$json_dir/test.json            \
    cuda_device=$cuda_device                         \
    allennlp train $config_file                      \
    --serialization-dir $models_dir/$experiment_name \
    --include-package src.ner.dygie.models.dygie     \
    --include-package ner.dygie.data_readers.dataset_readers.ie_json
    # --cache-directory $data_root/cached             
