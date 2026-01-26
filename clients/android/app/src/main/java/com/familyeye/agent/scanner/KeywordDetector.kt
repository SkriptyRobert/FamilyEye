package com.familyeye.agent.scanner

import java.util.*

/**
 * High-performance keyword detector using the Aho-Corasick algorithm.
 * Optimized for scanning large text blocks against many keywords simultaneously.
 * Supports accent-insensitive and case-insensitive matching.
 */
class KeywordDetector(keywords: List<String>) {
    
    private class Node {
        val next = mutableMapOf<Char, Node>()
        var failure: Node? = null
        var isEndOfKeyword = false
        var keyword: String? = null
    }

    private val root = Node()

    init {
        // Build Trie
        for (keyword in keywords) {
            var current = root
            val normalizedKeyword = normalize(keyword)
            for (char in normalizedKeyword) {
                current = current.next.getOrPut(char) { Node() }
            }
            current.isEndOfKeyword = true
            current.keyword = keyword // Store original for reporting
        }

        // Build failure links using BFS
        val queue: Queue<Node> = LinkedList()
        for (node in root.next.values) {
            node.failure = root
            queue.add(node)
        }

        while (queue.isNotEmpty()) {
            val u = queue.poll()
            for ((char, v) in u.next) {
                var f = u.failure
                while (f != null && !f.next.containsKey(char)) {
                    f = f.failure
                }
                v.failure = f?.next?.get(char) ?: root
                queue.add(v)
            }
        }
    }

    private fun normalize(input: String?): String {
        if (input == null) return ""
        val temp = java.text.Normalizer.normalize(input, java.text.Normalizer.Form.NFD)
        val pattern = java.util.regex.Pattern.compile("\\p{InCombiningDiacriticalMarks}+")
        return pattern.matcher(temp).replaceAll("").lowercase(Locale.getDefault())
    }

    /**
     * Scans text for any of the keywords.
     * Returns the first found keyword or null.
     */
    fun findAny(text: String): String? {
        var current = root
        val normalizedText = normalize(text)

        for (char in normalizedText) {
            while (current != root && !current.next.containsKey(char)) {
                current = current.failure ?: root
            }
            current = current.next[char] ?: root
            
            // Check current node and all its failure link ancestors for matches
            var temp: Node? = current
            while (temp != null && temp != root) {
                if (temp.isEndOfKeyword) {
                    return temp.keyword
                }
                temp = temp.failure
            }
        }
        return null
    }
}
