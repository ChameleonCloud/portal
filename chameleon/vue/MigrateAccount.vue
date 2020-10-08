<template>
<div class="row">
  <div class="col-md-4">
    <div class="panel panel-default">
      <div class="panel-heading">
        <h4 class="panel-title">Your user</h4>
      </div>
      <div class="empty" v-if="loading">
        <p>Loading your user&hellip;</p>
      </div>
      <div class="userProject" v-else>
        <div class="userProject_heading">
          <span class="title">{{ user.name }}</span>
          <button class="migrateButton btn"
            :class="{ 'btn-default': user.migratedAt, 'btn-primary': !user.migratedAt }"
            @click="migrateUser()">
            <span v-if="user.migratedAt">Re-run migration</span>
            <span v-else>Migrate</span>
          </button>
        </div>
      </div>
    </div>
    <div class="panel panel-default">
      <div class="panel-heading">
        <h4 class="panel-title">Projects</h4>
      </div>
      <div class="empty" v-if="loading">
        <p>Loading your projects&hellip;</p>
      </div>
      <div v-else>
        <ul class="userProjects">
          <li class="userProject" v-for="project in projects"
            :key="project.chargeCode">
            <div class="userProject_heading">
              <span class="title">{{ project.name }}</span>
              <button class="migrateButton btn"
                :class="{ 'btn-default': project.migratedAt, 'btn-primary': !project.migratedAt }"
                @click="migrateProject(project.chargeCode)">
                <span v-if="project.migratedAt">Re-run migration</span>
                <span v-else>Migrate</span>
              </button>
            </div>
            <div v-if="project.migratedAt">
              <span class="badge badge-success">Migrated</span>
              <span>on {{ migratedAt(project) }}</span>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="col-md-8">
    <div class="panel panel-default"
      :class="{
        'panel-success': migrationSucceeded,
        'panel-danger': migrationFailed
      }">
      <div class="panel-heading" v-if="migrationStatus">
        <h4 class="panel-title">
          <span v-if="migrationSucceeded">Migration completed</span>
          <span v-else-if="migrationFailed">Migration failed</span>
          <span v-else>Migration in progress</span>
        </h4>
      </div>
      <div class="migrationStatus" v-if="migrationStatus">
        <div class="progress">
          <div class="progress-bar"
            :class="{
              'progress-bar-success': migrationSuccess,
              'progress-bar-danger': migrationFailed
            }"
            :style="{ width: migrationPercentage + '%' }"></div>
        </div>
        <h4>Log</h4>
        <pre>{{ migrationStatus.messages.join('\n') }}</pre>
      </div>
      <div class="empty lalign" v-else>
        <div>
          <p>Select a user or project to start (or re-run) a migration.</p>
          <p>
            A <strong>user migration</strong> ensures any SSH keypairs uploaded
            in the past are transferred over to your new account.
          </p>
          <p>
            A <strong>project migration</strong> ensures any disk images or
            snapshots associated with the project are transferred to the new
            account. Disk images and snapshots will still be accessible via the
            old account, so this is non-destructive. Any member of the project
            can initiate a migration.
          </p>
        </div>
      </div>
    </div>
  </div>
</div>
</template>

<style scoped>
.userProjects {
  list-style: none;
  padding-left: 0;
}

.userProject {
  box-sizing: border-box;
  padding: 10px 15px 15px;
  border-bottom: 1px solid #dedede;
} .userProject:last-child {
  border-bottom: none;
} .userProject_heading {
  display: flex;
  align-items: center;
  margin-bottom: .5rem;
} .userProject_heading .title {
  flex: 1;
  margin: 0;
} .userProject .badge {
  margin-right: .5rem;
} .userProject .badge-success {
  background-color: #74a93c;
}

.migrationStatus {
  padding: 2rem;
}

.empty {
  text-align: center;
  display: flex;
  align-items: center;
  padding: 2rem;
} .empty > * {
  flex: 1;
} .empty.lalign {
  text-align: left;
}
</style>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      loading: true,
      user: {},
      projects: [],
      activeMigrations: new Map(),
      migrationStatus: null,
    }
  },
  computed: {
    migrationSucceeded() {
      return this.migrationStatus && this.migrationStatus.state === 'SUCCESS'
    },
    migrationFailed() {
      return this.migrationStatus && this.migrationStatus.state === 'FAILURE'
    },
    migrationPercentage() {
      // Default to 1% if we haven't fetched the job info yet to at least
      // move the meter a bit.
      const { progress_pct = 1 } = this.migrationStatus || {}
      return progress_pct
    }
  },
  methods: {
    migratedAt(resource) {
      return new Date(resource.migratedAt).toLocaleString('en-US')
    },
    refresh() {
      axios
        .get('/api/user/migrate/status/')
        .then(response => {
          const { user, projects } = response.data
          this.projects = projects
          this.user = user
        })
        .catch(error => {
          this.errored = true
        })
        .finally(() => this.loading = false)
    },
    startMigration(jobId, migrationType, extraArgs={}) {
      const createTimer = () => {
        return setInterval(this.pollMigration.bind(this, jobId), 3000)
      }
      this.clearPollers()
      if (! this.activeMigrations.has(jobId)) {
        this.migrationStatus = {
          messages: [`Starting ${migrationType} migration...`],
          progress_pct: 0
        }
        axios
          .post('/api/user/migrate/job/', {
            migrationType,
            ...extraArgs
          })
          .then(response => {
            this.activeMigrations.set(jobId, {
              timer: createTimer(),
              taskId: response.data.taskId
            })
          })
          .catch(error => {
            console.log(error)
          })
      } else {
        const migration = this.activeMigrations.get(jobId)
        migration.timer = createTimer()
        // Immediately update for quick feedback
        this.migrationStatus = migration.lastStatus
      }
    },
    migrateProject(chargeCode) {
      this.startMigration(chargeCode, 'project', { chargeCode })
    },
    migrateUser() {
      this.startMigration('user', 'user')
    },
    onMigrationFinished() {
      this.clearPollers()
      // Re-load projects to display new migration status
      this.refresh()
    },
    clearPollers() {
      for (const [, migration] of this.activeMigrations) {
        if (migration.timer) {
          clearInterval(migration.timer)
          migration.timer = null
        }
      }
    },
    pollMigration(jobId) {
      if (! this.activeMigrations.has(jobId)) {
        console.log(`No migration is running for job ${jobId}`)
        return
      }

      const migration = this.activeMigrations.get(jobId)

      axios
        .get(`/api/user/migrate/job/?task_id=${migration.taskId}`)
        .then(response => {
          this.migrationStatus = migration.lastStatus = response.data
          if (this.migrationSucceeded || this.migrationFailed) {
            this.onMigrationFinished()
          }
        })
        .catch(error => {
          console.log(error)
        })
    }
  },
  mounted() {
    this.refresh()
  }
}
</script>
