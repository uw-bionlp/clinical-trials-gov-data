HERE=$PWD
NEURONER_DIR=~/work/nlp/NeuroNER-kahyun
NEURONER_DATA_DIR=$NEURONER_DIR/data/clinical-trials-gov
SERVER=web79
SERVER_DATA_DIR=/data/www/brat/data/clinical-trials-gov

# Clear previous neuroner data
cd $NEURONER_DIR                                                             && \
source venv/bin/activate                                                     && \
rm -rf output                                                                && \
rm -f $NEURONER_DATA_DIR/*_spacy.txt                                         && \
rm -f $NEURONER_DATA_DIR/train/*                                             && \
rm -f $NEURONER_DATA_DIR/valid/*                                             && \

# Add latest data
cp $HERE/ner/nic/training/* $NEURONER_DATA_DIR/valid                         && \
cp $HERE/ner/nic/batch11/* $NEURONER_DATA_DIR/train                                         
            
# Run neuroner            
cd src                                                                       && \
python3 main.py                                                                 \
    --dataset_text_folder=../data/clinical-trials-gov                           \
    --train_model=True                                                          \
    --use_pretrained_model=False                                                \
    --optimizer=adam                                                            \
    --learning_rate=0.001                                                       \
    --output_folder=../output                                                && \

# Get output directory
cd $NEURONER_DIR
OUTPUT_DIR="$(find output -maxdepth 1 -type d -name 'clinical-trials-gov*')" && \

# Clear previous BRAT data
ssh $SERVER "cd $SERVER_DATA_DIR && rm ner/predict/*"                        && \

# Copy new data
scp $OUTPUT_DIR/brat/deploy/* $SERVER:$SERVER_DATA_DIR/ner/predict           && \
cd $HEREbatch