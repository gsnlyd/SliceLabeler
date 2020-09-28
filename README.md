## Browser-based GUI for labeling MRI volumes and slices.
### Python Version:
The latest version of Python 3 is recommended.

Python 3.6 or newer is required.
### Installation:
First, clone the repo and cd into the new directory.

Then, create a python virtual environment and install the dependencies:
#### Mac/Linux:
```shell script
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Windows CMD:
```
python3 -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Usage:
#### Mac/Linux:
```shell script
source venv/bin/activate
export FLASK_APP=application.py
flask run
```
#### Windows CMD:
```
venv\Scripts\activate.bat
set FLASK_APP=application.py
flask run
```

To deactivate the virtual environment when you're done:
```shell script
deactivate
```

### See also:
- [Venv documentation](https://docs.python.org/3/library/venv.html)
- [Flask documentation](https://flask.palletsprojects.com/en/1.1.x/quickstart/)
