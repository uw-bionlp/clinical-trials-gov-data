HERE=/home/nic/class/clinical-trials-gov
DIR=/data/www/brat/data/clinical-trials-gov

python3 $HERE/scripts/infer_criteria.py
cd $HERE/logical_bounds
tar -czf logical_bounds.tar.gz ./
ssh web79 "cd $DIR && rm -rf logical_bounds"
scp -r logical_bounds.tar.gz web79:/data/www/brat/data/clinical-trials-gov
rm logical_bounds.tar.gz
ssh web79 "cd $DIR && mkdir logical_bounds && mv logical_bounds.tar.gz logical_bounds && cd logical_bounds && tar -xzf logical_bounds.tar.gz && rm logical_bounds.tar.gz && mv auto zz_auto_do_not_edit && cd .. && chmod 777 -R logical_bounds"
cd $HERE
