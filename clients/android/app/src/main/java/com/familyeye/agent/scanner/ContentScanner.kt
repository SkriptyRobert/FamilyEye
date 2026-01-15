package com.familyeye.agent.scanner

import android.view.accessibility.AccessibilityNodeInfo
import com.familyeye.agent.service.AppDetectorService
import com.familyeye.agent.data.api.dto.ShieldKeyword
import kotlinx.coroutines.*
import timber.log.Timber
import java.util.Locale
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ContentScanner @Inject constructor(
    private val keywordManager: KeywordManager
) {
    private val scannerScope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var lastScanTime = 0L
    private val SCAN_INTERVAL_MS = 2000L // Min interval between scans (Battery Saver)
    
    // Ignore these high-refresh apps to save battery
    private val IGNORED_PACKAGES = setOf(
        "com.google.android.youtube",
        "com.netflix.mediaclient",
        "com.spotify.music"
    )

    fun processScreen(rootNode: AccessibilityNodeInfo?, currentPackage: String?) {
        if (rootNode == null || currentPackage == null) return
        
        // 1. Package Filter
        if (IGNORED_PACKAGES.contains(currentPackage)) return

        // 2. Rate Limit (Debounce)
        val now = System.currentTimeMillis()
        if (now - lastScanTime < SCAN_INTERVAL_MS) return
        lastScanTime = now

        // 3. Process Async
        scannerScope.launch {
            try {
                val textContent = extractText(rootNode)
                if (textContent.isNotEmpty()) {
                    scanForKeywords(textContent, currentPackage)
                }
            } catch (e: Exception) {
                Timber.e(e, "Error during content scan")
            }
        }
    }

    private fun extractText(node: AccessibilityNodeInfo): StringBuilder {
        val sb = StringBuilder()
        
        // DFS Traversal to get all text
        // Limit depth/count to prevent freezing on huge lists
        val stack = java.util.Stack<AccessibilityNodeInfo>()
        stack.push(node)
        
        var nodeCount = 0
        val MAX_NODES = 500 // Increased from 50 to cover complex web pages (Chrome DOM)
        
        while (stack.isNotEmpty() && nodeCount < MAX_NODES) {
            val currentNode = stack.pop()
            nodeCount++
            
            if (currentNode.text != null && currentNode.text.isNotEmpty()) {
                sb.append(currentNode.text).append(" ")
            }
            // Also check contentDescription (often used in WebViews/Images)
            if (currentNode.contentDescription != null && currentNode.contentDescription.isNotEmpty()) {
                sb.append(currentNode.contentDescription).append(" ")
            }
            
            // Add children
            for (i in 0 until currentNode.childCount) {
                currentNode.getChild(i)?.let { stack.push(it) }
            }
        }
        return sb
    }

    private suspend fun scanForKeywords(text: StringBuilder, packageName: String) {
        val content = text.toString().lowercase(Locale.getDefault())
        val keywords = keywordManager.getKeywords()
        
        for (kw in keywords) {
            if (kw.enabled && content.contains(kw.keyword)) {
                Timber.w("SMART SHIELD: Detected '${kw.keyword}' in $packageName")
                handleDetection(kw, packageName, content)
                break // Report one match per scan to avoid spam
            }
        }
    }

    private suspend fun handleDetection(keyword: ShieldKeyword, packageName: String, contextText: String) {
        // Find instance of AppDetectorService to trigger screenshot
        AppDetectorService.instance?.let { service ->
             service.handleSmartShieldDetection(keyword, packageName, contextText)
        }
    }
}
