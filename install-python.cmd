curl https://www.python.org/ftp/python/3.13.0/python-3.13.0-embed-amd64.zip -o python.zip
tar -xf python.zip
del python.zip

curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python.exe -m get-pip
del get-pip.py

echo import site >> python313._pth
python.exe -m pip install setuptools