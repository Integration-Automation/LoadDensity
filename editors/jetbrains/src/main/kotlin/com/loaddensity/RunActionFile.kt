package com.loaddensity

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.process.OSProcessHandler
import com.intellij.execution.process.ProcessTerminatedListener
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.vfs.VirtualFile

class RunActionFile : AnAction() {
    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        val file: VirtualFile = event.getData(CommonDataKeys.VIRTUAL_FILE) ?: return
        if (file.extension?.lowercase() != "json") {
            Messages.showWarningDialog(project,
                "Selected file is not a JSON file.", "LoadDensity")
            return
        }
        val command = GeneralCommandLine("loaddensity", "run", file.path)
            .withWorkDirectory(project.basePath)
        val handler = OSProcessHandler(command)
        ProcessTerminatedListener.attach(handler)
        handler.startNotify()
    }
}
