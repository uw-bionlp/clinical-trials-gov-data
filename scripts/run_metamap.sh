PARSER_DIR=~/work/covid-parser
HERE=$PWD
MM_SEMATIC_TYPES="dsyn lbtr clnd topp aggp clna orgf orga mobd lang"

cd $PARSER_DIR
source venv/bin/activate
cd $HERE

for dir in `find docs -type d`; do
    cd $PARSER_DIR

    if [ $dir != "docs" ]; then

        base=`basename $dir`
        ./covid-parser.sh $HERE/$dir                           \
            --metamap                                          \
            --metamap_semantic_types $MM_SEMATIC_TYPES         \
            --output_path $HERE/ner/metamap/$base              \
            --threads=4
    fi
    
done

cd $HERE