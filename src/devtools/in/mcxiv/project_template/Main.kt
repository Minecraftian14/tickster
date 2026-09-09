package `in`.mcxiv.project_template

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.safeContentPadding
import androidx.compose.material.Button
import androidx.compose.material.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import com.composables.ui.theme.ComposablesTheme
import com.composables.ui.theme.colors
import com.composables.ui.theme.onPrimaryColor
import com.composables.ui.theme.panelColor
import com.composables.ui.theme.primaryColor
import com.composeunstyled.theme.Theme

fun main() = application {
    Window(
        onCloseRequest = ::exitApplication,
        title = "project-template",
    ) {
        App()
    }
}

@Composable
@Preview
fun App() {
    ComposablesTheme {
        var showContent by remember { mutableStateOf(false) }
        Column(
            modifier = Modifier
                .background(Theme[colors][panelColor])
                .safeContentPadding()
                .fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Button(onClick = { showContent = !showContent }) {
                Text("Click me!")
            }
            AnimatedVisibility(showContent) {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text("Compose: Hello")
                }
            }
        }
    }
}