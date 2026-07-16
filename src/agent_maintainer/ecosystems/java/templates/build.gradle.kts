plugins {
    java
    id("com.diffplug.spotless") version "@SPOTLESS_PLUGIN_VERSION@"
    id("com.github.spotbugs") version "@SPOTBUGS_PLUGIN_VERSION@"
    checkstyle
    pmd
    jacoco
}

spotless {
    java {
        googleJavaFormat("@GOOGLE_JAVA_FORMAT_VERSION@")
        importOrder()
        removeUnusedImports()
        trimTrailingWhitespace()
        endWithNewline()
    }
}

spotbugs {
    effort = com.github.spotbugs.snom.Effort.MAX
    reportLevel = com.github.spotbugs.snom.Confidence.MEDIUM
}

checkstyle {
    toolVersion = "@CHECKSTYLE_VERSION@"
    configFile = file("config/checkstyle/checkstyle.xml")
}

pmd {
    toolVersion = "@PMD_VERSION@"
    ruleSets = emptyList()
    ruleSetFiles = files("config/pmd/pmd.xml")
}

jacoco {
    toolVersion = "@JACOCO_VERSION@"
}
