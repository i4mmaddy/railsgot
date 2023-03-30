pipeline{
  agent any 
  stages{
    stage('CICD'){
      steps{
         sh 'pip install --extra-index-url https://test.pypi.org/simple/ boman-cli-uat==0.21'
         sh '~/.local/bin/boman-cli-uat -a run -u https://dashboard.boman.ai/v2/ -cicd jenkins'
      }
    }
  }
}
