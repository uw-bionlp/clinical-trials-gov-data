HERE=~/class/clinical-trials-gov
DIR=/data/www/brat/data/clinical-trials-gov

#python3 $HERE/scripts/metamap_to_brat.py
cd $HERE
tar -czf ner.tar.gz ner
ssh web79 "cd $DIR && rm -rf ner"
scp ner.tar.gz web79:/data/www/brat/data/clinical-trials-gov
rm ner.tar.gz
ssh web79 "cd $DIR && tar -xzf ner.tar.gz && rm ner.tar.gz && cd ner && rm -rf metamap && mv auto .auto && cd .. && chmod 777 -R ner"
cd $HERE
