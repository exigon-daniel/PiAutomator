DIR=$( cd "$( dirname $0 )" && pwd )
echo $DIR
source $DIR/../piautomatorenv/bin/activate
pip install -r $DIR/../conf/requirements.txt
$DIR/start-automator.py
