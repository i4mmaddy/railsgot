pipeline{
  agent any 
  stages{
    stage('CICD'){
      steps{
         sh 'pip install --extra-index-url https://test.pypi.org/simple/ boman-cli-uat==0.22'
         sh '~/.local/bin/boman-cli-uat -a run -cicd jenkins -fb only-critical'
      }
    }
  }
}
