pipeline{
  agent any 
  stages{
    stage('CICD'){
      steps{
         sh '~/.local/bin/boman-cli-uat -a run -cicd jenkins -fb only-high'
      }
    }
  }
}
