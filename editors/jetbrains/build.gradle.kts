plugins {
    id("org.jetbrains.kotlin.jvm") version "1.9.23"
    id("org.jetbrains.intellij") version "1.17.3"
}

group = "com.loaddensity"
version = "0.1.0"

repositories { mavenCentral() }

dependencies {
    implementation(kotlin("stdlib"))
}

intellij {
    version.set("2024.1")
    type.set("IC")
    plugins.set(listOf("com.intellij.java"))
    // The plugin's default is "download sources unless $CI is set", which resolves a different
    // IDE artifact locally than in CI and breaks the dependency lock. Pin it to one answer.
    downloadSources.set(false)
}

tasks {
    patchPluginXml {
        sinceBuild.set("241")
        untilBuild.set("251.*")
    }
}

// Every resolved configuration is pinned in gradle.lockfile; refresh it with
//   gradle dependencies --write-locks
dependencyLocking {
    lockAllConfigurations()
}
