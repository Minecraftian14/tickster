import org.jetbrains.compose.desktop.application.dsl.TargetFormat

plugins {
    alias(libs.plugins.kotlinJvm)
    alias(libs.plugins.composeMultiplatform)
    alias(libs.plugins.composeCompiler)
}

group = "in.mcxiv"
version = "1.0-SNAPSHOT"

dependencies {
    implementation(libs.compose.runtime)
    implementation(libs.compose.foundation)
    implementation(libs.compose.ui)
    implementation(libs.compose.components.resources)
    implementation(libs.compose.uiToolingPreview)
    implementation(libs.androidx.lifecycle.viewmodelCompose)
    implementation(libs.androidx.lifecycle.runtimeCompose)
    implementation(libs.kotlinx.serializationJson)

    implementation(libs.composables.ui)
    implementation(libs.composables.icons)

    implementation(compose.desktop.currentOs)
    implementation(libs.kotlinx.coroutinesSwing)

    testImplementation(libs.kotlin.test)
}

compose.desktop {
    application {
        mainClass = "in.mcxiv.project_template.MainKt"

        nativeDistributions {
            targetFormats(TargetFormat.Dmg, TargetFormat.Msi, TargetFormat.Deb)
            packageName = "in.mcxiv.project_template"
            packageVersion = "1.0.0"
        }
    }
}

sourceSets {
    main {
        kotlin.setSrcDirs(listOf("src/devtools"))
        resources.setSrcDirs(listOf("src/resources"))
    }

    test {
        kotlin.setSrcDirs(listOf("tests/devtools"))
        resources.setSrcDirs(listOf("tests/resources"))
    }
}
