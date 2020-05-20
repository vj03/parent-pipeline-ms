#!groovy
supportedEnvs = ['devx', 'qax', 'stgx', 'stgxdr', 'prod', 'prod-eu']
regions = ['us-east-1', 'eu-central-1']
size = ['1', '2', '3', '4', '100']
formula = ['Deploy Formula']
provisioningApiEndpoints = [
  'http://internal-diasprovisioningapi-devx-1138163774.us-east-1.elb.amazonaws.com',
  'http://internal-diasprovisioningapi-stgx-871362975.us-east-1.elb.amazonaws.com',
  'http://internal-diasprovisioningapi-qax-1487899448.us-east-1.elb.amazonaws.com'
]

properties([
  parameters([
    choice(name: 'Environment', description: 'Environment', choices: '\n' + supportedEnvs.join('\n')),
    choice(name: 'Region', description: 'Target region', choices: '\n' + regions.join('\n')),
    string(name: 'ClientID', description: 'Client ID (must be single ClientID)', defaultValue: ''),
    string(name: 'Description', description: 'Description', defaultValue: ''),
    string(name: 'OrgID', description: 'Org ID', defaultValue: ''),
    string(name: 'SKU', description: 'SKU', defaultValue: ''),
    booleanParam(name: 'SkipApprovals', description: 'Only build stages that do not require approval', defaultValue: false),
    string(name: 'TFS3Version', description: 'tf-dias-generic-st-s3 git tag to deploy', defaultValue: ''),
    string(name: 'TFElasticVersion', description: 'tf-dias-generic-st-elastic git tag to deploy', defaultValue: ''),
    string(name: 'TFLogstashVersion', description: 'tf-dias-generic-st-logstash git tag to deploy', defaultValue: ''),
    string(name: 'DIASBranch', description: 'dias-generic-provisioning-tools git branch to use', defaultValue: 'master'),
    string(name: 'TFS3Branch', description: 'tf-dias-generic-st-s3 git branch to use', defaultValue: 'master'),
    string(name: 'TFElasticBranch', description: 'tf-dias-generic-st-elastic git branch to use', defaultValue: 'master'),
    string(name: 'TFLogstashBranch', description: 'tf-dias-generic-st-logstash git branch to use', defaultValue: 'master'),
    string(name: 'FormulaLogstashBranch', description: 'formula-dias-generic-st-logstash git branch to use', defaultValue: 'master'),
    booleanParam(name: 'ForceInfluxRecreate', description: 'Force creation of new InfluxDB to replace existing', defaultValue: false),
    booleanParam(name: 'Destroy', description: 'Destroy environment?', defaultValue: false),
    choice(name: 'FormulaBatchSize', choices: '\n' + size.join('\n'), description: 'Batch size (how many hosts to run Salt on in parallel)'),
    choice(name: 'FormulaOperation', choices: '\n' + formula.join('\n'), description: 'Formula'),
    choice(name: 'DiasProvisioningApiEndpoint', description: 'DIAS Provisioning API Endpoint (blank for default)', choices: '\n' + provisioningApiEndpoints.join('\n')),
  ]),
  pipelineTriggers([])
])

if (!env.ClientID) {
  echo 'Specify a ClientID in order to start parent pipeline'
  return
}

// Change build display name
currentBuild.displayName = "${env.ClientID} - ${env.BRANCH_NAME} - ${env.Environment} - ${env.Region}"

// AWS credentials
def vault = new com.mulesoft.Vault()
vault.auth()

aws_info = vault.read("secret/aws/${env.Environment}")
env.AWS_ACCESS_KEY_ID = aws_info.access_key
env.AWS_SECRET_ACCESS_KEY = aws_info.secret_key
env.AWS_DEFAULT_REGION = env.Region

// Utility functions
def getShellOutput(command) {
  output = sh(script: command, returnStdout: true)
  return output.trim()
}

def installPythonRequirements() {
  env.PYTHONUSERBASE = env.WORKSPACE
  sh 'pip install --user -r requirements.txt'
}

pipeline {
  agent any
  stages {
    stage("Client ID Check") {
      when {
        expression { env.Destroy == 'false' }
      }
      steps {
        script {
          node("${env.Environment}-slave-shared") {
            checkout scm

            installPythonRequirements()
            orgID = getShellOutput("python helper.py -c ${env.ClientID}")
            sku = getShellOutput("python helper.py -o ${env.OrgID}")
          }

          timeout(time: 1, unit: 'HOURS') {
            if (orgID) {
              input(
                id: 'ClientExistsConfirm',
                message: "${env.ClientID} data already exists and is possibly already set up"
              )
            } else if (sku) {
              input(
                id: 'OrgAlreadyInUse',
                message: "${env.OrgID} already in use for another single tenant"
              )
            }
          }
        }
      }
    }
    stage("Creating initial SSM parameters") {
      when {
        expression { env.Destroy == 'false' }
      }
      steps {
        build job: "../dias-generic-provisioning-tools/${env.DIASBranch}", parameters: [
          string(name: 'Operation',   value: 'Create initial SSM parameters'),
          string(name: 'Environment', value: "${env.Environment}"),
          string(name: 'Region',      value: "${env.Region}"),
          string(name: 'ClientID',    value: "${env.ClientID}"),
          string(name: 'Description', value: "${env.Description}"),
          string(name: 'OrgID',       value: "${env.OrgID}"),
          string(name: 'SKU',         value: "${env.SKU}")
        ]
      }
    }

    stage("Creating InfluxDB cluster") {
      when {
        expression { env.Destroy == 'false' }
      }
      steps {
        build job: "../dias-generic-provisioning-tools/${env.DIASBranch}", parameters: [
          string(name: 'Operation',                 value: 'Create InfluxDB cluster'),
          string(name: 'Environment',               value: "${env.Environment}"),
          string(name: 'Region',                    value: "${env.Region}"),
          string(name: 'ClientID',                  value: "${env.ClientID}"),
          string(name: 'OrgID',                     value: "${env.OrgID}"),
          booleanParam(name: 'ForceInfluxRecreate', value: env.ForceInfluxRecreate.toBoolean())
        ]
      }
    }

    stage("Creating InfluxDB tables") {
      when {
        expression { env.Destroy == 'false' }
      }
      steps {
        build job: "../dias-generic-provisioning-tools/${env.DIASBranch}", parameters: [
          string(name: 'Operation',   value: 'Create InfluxDB tables'),
          string(name: 'Environment', value: "${env.Environment}"),
          string(name: 'Region',      value: "${env.Region}"),
          string(name: 'ClientID',    value: "${env.ClientID}"),
          string(name: 'OrgID',       value: "${env.OrgID}")
        ]
      }
    }

    stage("Creating Internal InfluxDB tables") {
      when {
        expression { env.Destroy == 'false' }
      }
      steps {
        build job: "../dias-generic-provisioning-tools/${env.DIASBranch}", parameters: [
          string(name: 'Operation',   value: 'Create Internal InfluxDB tables'),
          string(name: 'Environment', value: "${env.Environment}"),
          string(name: 'Region',      value: "${env.Region}"),
          string(name: 'ClientID',    value: "${env.ClientID}")
        ]
      }
    }

    stage("Building tf-dias-generic-st-s3") {
      when {
        expression { env.Destroy == 'false' }
        expression { env.SkipApprovals == 'false' }
      }
      steps {
        build job: "../../DevOps/terraform/tf-dias-generic-st-s3/${env.TFS3Branch}", parameters: [
          string(name: 'Operation',     value: 'Deploy Terraform'),
          string(name: 'Environment',   value: "${env.Environment}"),
          string(name: 'Region',        value: "${env.Region}"),
          string(name: 'ClientID',      value: "${env.ClientID}"),
          booleanParam(name: 'Destroy', value: false),
          string(name: 'Version',       value: "${env.TFS3Version}")
        ]
      }
    }

    stage("Building tf-dias-generic-st-elastic") {
      when {
        expression { env.Destroy == 'false' }
        expression { env.SkipApprovals == 'false' }
      }
      steps {
        build job: "../../DevOps/terraform/tf-dias-generic-st-elastic/${env.TFElasticBranch}", parameters: [
          string(name: 'Operation',     value: 'Deploy Terraform'),
          string(name: 'Environment',   value: "${env.Environment}"),
          string(name: 'Region',        value: "${env.Region}"),
          string(name: 'ClientID',      value: "${env.ClientID}"),
          booleanParam(name: 'Destroy', value: false),
          string(name: 'Version',       value: "${env.TFElasticVersion}")
        ]
      }
    }

    stage("Building tf-dias-generic-st-logstash") {
      when {
        expression { env.Destroy == 'false' }
        expression { env.SkipApprovals == 'false' }
      }
      steps {
        build job: "../../DevOps/terraform/tf-dias-generic-st-logstash/${env.TFLogstashBranch}", parameters: [
          string(name: 'Operation',     value: 'Deploy Terraform'),
          string(name: 'Environment',   value: "${env.Environment}"),
          string(name: 'Region',        value: "${env.Region}"),
          string(name: 'ClientID',      value: "${env.ClientID}"),
          booleanParam(name: 'Destroy', value: false),
          string(name: 'Version',       value: "${env.TFLogstashVersion}")
        ]
      }
    }

    stage("Creating Anypoint Monitoring Environment") {
      when {
        expression { env.Destroy == 'false' }
        expression { env.SkipApprovals == 'false' }
      }
      steps {
        build job: "../dias-generic-provisioning-tools/${env.DIASBranch}", parameters: [
          string(name: 'Operation',   value: 'Create Anypoint Monitoring Environment'),
          string(name: 'Environment', value: "${env.Environment}"),
          string(name: 'Region',      value: "${env.Region}"),
          string(name: 'ClientID',    value: "${env.ClientID}"),
          string(name: 'OrgID',       value: "${env.OrgID}"),
          string(name: 'DiasProvisioningApiEndpoint', value: "${env.DiasProvisioningApiEndpoint}")
        ]
      }
    }

    stage("Building formula-dias-generic-st-logstash") {
      when {
        expression { env.Destroy == 'false' }
        expression { env.SkipApprovals == 'false' }
      }
      steps {
        build job: "../../DevOps/salt-formula/formula-dias-generic-st-logstash/${env.FormulaLogstashBranch}", parameters: [
          string(name: 'Operation',   value: "${env.FormulaOperation}"),
          string(name: 'Environment', value: "${env.Environment}"),
          string(name: 'ClientID',    value: "${env.ClientID}"),
          string(name: 'BatchSize',   value: "${env.FormulaBatchSize}")
        ]
      }
    }

    stage("Creating Anypoint Monitoring Dashboard") {
      when {
        expression { env.Destroy == 'false' }
        expression { env.SkipApprovals == 'false' }
      }
      steps {
        build job: "../dias-generic-provisioning-tools/${env.DIASBranch}", parameters: [
          string(name: 'Operation',   value: 'Create Anypoint Monitoring Dashboard'),
          string(name: 'Environment', value: "${env.Environment}"),
          string(name: 'Region',      value: "${env.Region}"),
          string(name: 'ClientID',    value: "${env.ClientID}"),
          string(name: 'OrgID',       value: "${env.OrgID}"),
          string(name: 'DiasProvisioningApiEndpoint', value: "${env.DiasProvisioningApiEndpoint}")
        ]
      }
    }

    stage("End to end tests") {
      when {
        expression { env.Destroy == 'false' }
        expression { env.SkipApprovals == 'false' }
      }
      steps {
        build job: "../dias-generic-provisioning-tools/${env.DIASBranch}", parameters: [
          string(name: 'Operation', value: 'Execute end to end test'),
          string(name: 'ClientID',  value: "${env.ClientID}")
        ]
      }
    }

    stage("Destroying tf-dias-generic-st-logstash") {
      when {
        expression { env.Destroy == 'true' }
        expression { env.SkipApprovals == 'false' }
      }
      steps {
        build job: "../../DevOps/terraform/tf-dias-generic-st-logstash/${env.TFLogstashBranch}", parameters: [
          string(name: 'Operation',     value: 'Deploy Terraform'),
          string(name: 'Environment',   value: "${env.Environment}"),
          string(name: 'Region',        value: "${env.Region}"),
          string(name: 'ClientID',      value: "${env.ClientID}"),
          booleanParam(name: 'Destroy', value: true)
        ]
      }
    }

    stage("Destroying tf-dias-generic-st-elastic") {
      when {
        expression { env.Destroy == 'true' }
        expression { env.SkipApprovals == 'false' }
      }
      steps {
        build job: "../../DevOps/terraform/tf-dias-generic-st-elastic/${env.TFElasticBranch}", parameters: [
          string(name: 'Operation',     value: 'Deploy Terraform'),
          string(name: 'Environment',   value: "${env.Environment}"),
          string(name: 'Region',        value: "${env.Region}"),
          string(name: 'ClientID',      value: "${env.ClientID}"),
          booleanParam(name: 'Destroy', value: true)
        ]
      }
    }

    stage("Destroying tf-dias-generic-st-s3") {
      when {
        expression { env.Destroy == 'true' }
        expression { env.SkipApprovals == 'false' }
      }
      steps {
        build job: "../../DevOps/terraform/tf-dias-generic-st-s3/${env.TFS3Branch}", parameters: [
          string(name: 'Operation',     value: 'Deploy Terraform'),
          string(name: 'Environment',   value: "${env.Environment}"),
          string(name: 'Region',        value: "${env.Region}"),
          string(name: 'ClientID',      value: "${env.ClientID}"),
          booleanParam(name: 'Destroy', value: true)
        ]
      }
    }
  } // end stages
} // end pipeline
