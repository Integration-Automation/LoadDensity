package com.loaddensity

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.content.ContentFactory
import javax.swing.JLabel

class LoadDensityToolWindowFactory : ToolWindowFactory {
    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val label = JLabel("<html>LoadDensity tool window<br/>" +
                "Use the editor action to run an action JSON.</html>")
        val content = ContentFactory.getInstance().createContent(label, "", false)
        toolWindow.contentManager.addContent(content)
    }
}
