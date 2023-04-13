pipeline{
  agent any 
  stages{
    stage('CICD'){
      steps{
         sh '~/.local/bin/boman-cli -a run -cicd jenkins '
      }
    }
  }
}
