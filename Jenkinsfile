pipeline{
  agent any 
  stages{
    stage('CICD'){
      steps{
         sh 'pip install --no-cache-dir --upgrade boman-cli'
         sh '~/.local/bin/boman-cli -a run -cicd jenkins -u https://devapi.boman.ai/v2/'
      }
    }
  }
}
