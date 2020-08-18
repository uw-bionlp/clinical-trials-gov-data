SERVER=web79
DATA_DIR=/data/www/brat/data/clinical-trials-gov
TAR_FILE=ner.tar.gz

# Pull latest annotations
ssh $SERVER "cd $DATA_DIR && tar -czf $TAR_FILE ner" && \
scp $SERVER:$DATA_DIR/ner.tar.gz ./                  && \

# Delete tar from server
ssh $SERVER "cd $DATA_DIR && rm $TAR_FILE"           && \

# Replace local annotations with those from server
rm -rf ner                                           && \
tar -xzf $TAR_FILE                                   && \
rm $TAR_FILE                                         && \

# Remove stats cache files
find ner -type f -name '.stats_cache' -delete