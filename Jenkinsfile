pipeline {
    agent any
    environment {
      HOME = "${env.WORKSPACE}"
      DOCKER_REGISTRY = 'docker.chameleoncloud.org'
      DOCKER_REGISTRY_CREDS = credentials('kolla-docker-registry-creds')
    }
    stages {
      stage('build') {
        steps {
          sh 'make build'
        }
      }
      stage('publish') {
        steps {
          sh 'docker login --username=$DOCKER_REGISTRY_CREDS_USR --password=$DOCKER_REGISTRY_CREDS_PSW $DOCKER_REGISTRY'
          sh 'make publish publish-latest'
        }
      }
    }

    post {
      always {
        sh 'docker logout $DOCKER_REGISTRY'
      }

      success {
        slackSend(
          channel: "#notifications",
          message: "*Build* of *Chameleon Portal* (${env.GIT_COMMIT.substring(0, 8)}) completed successfuly. <${env.RUN_DISPLAY_URL}|View build log>",
          color: "good"
        )
      }
    }
}
