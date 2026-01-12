# imms_fhir_api_automation

pytest-bdd Automation for Immunisation FHIR API

## Need to check in case any other libraries to be added

## Installation

This test pack requires Python 3.10 installed on the system or greater to run.

To execute the tests from your system, please follow the 4 easy steps below:

1. Clone the repo to any local folder
2. Create a virtual environment

    ```console
    # python -m venv .venv
    ```

3. Install all dependencies

    ```console
    # pip install -r .\requirements.txt
    ```

4. To activate env
   a. in git bash terminal
   `console
 source .venv/Scripts/activate
 `
   b. in Terminal
   `console
     .venv\Scripts\Activate.ps1
 `

5. Need to create .env file, please get in touch with Imms FHIR API Test team to get the content of the file

6. run following command to see that test are discovered

    ```console
       # pytest --collect-only
    ```

7. install and configure Aws CLI using following commands:
    1. pip install awscli
    2. aws configure
    3. if you want to use aws configure sso then install aws cli 2 and follow the instructions on AWS access key page.

8. to update the python packages run command 1 and to update requirement file run command 2.
    1. python -m pip install --upgrade <package name>
    2. python -m pip freeze > requirements.txt

----DO NOT USE BELOW---------------------------------------------

## Reporting

To create the json report -
pip install allure-behave

Command -
behave -f allure_behave.formatter:AllureFormatter -o output/allure-results

## To convert the json file to html in Allure Reporting

Dwnload the latest release allure-2.32.2.zip Allure Package from <https://github.com/allure-framework/allure2/releases>
Unzip the folder and add the bin directory to system variable path

Command to convert the json reports to html -
allure serve output/allure-results

Command to generate the html report manually if BROWSE does not work -
allure generate output/allure-results -o output/allure-report --clean

Start a http server to view the results -
python -m http.server

## To Open the index.html file

once the allure plug in place then we need to update the ymal with following code :
'''

- script: |
  source venv/bin/activate
  pytest --junitxml=output/test-results.xml --alluredir=output/allure-results || true
  displayName: 'Run Pytest-BDD tests with Allure'

- task: Bash@3
  displayName: 'Generate Allure Report'
  inputs:
  targetType: 'inline'
  script: |
  allure generate output/allure-results --clean -o output/allure-report

- script: ls -la output/allure-report
  displayName: 'List Allure Report Contents'

- task: PublishBuildArtifacts@1
  displayName: 'Publish Allure Report Artifact'
  inputs:
  pathToPublish: 'output/allure-report'
  artifactName: 'AllureReport'
  publishLocation: 'Pipeline'

'''
