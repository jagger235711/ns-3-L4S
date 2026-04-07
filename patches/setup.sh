cd /

git clone https://gitlab.com/nsnam/ns-3-dev.git ns-3.46
cd ns-3.46
git checkout ns-3.46

git am ../patches/l4s-implementation.patch

cp ../experiments/code.cc scratch/

./ns3 configure --enable-examples --enable-tests
./ns3 build

cd ns-3.46
python3 ../experiments/run-simulation.py

python3 ../experiments/create_master_dataset.py