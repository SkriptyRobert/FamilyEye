package com.familyeye.agent.scanner

import org.junit.Assert.*
import org.junit.Test
import java.util.Locale

class KeywordDetectorTest {

    @Test
    fun testBasicDetection() {
        val keywords = listOf("drogy", "gambling", "sebevrazda")
        val detector = KeywordDetector(keywords)
        
        assertEquals("drogy", detector.findAny("Tady jsou nejake drogy v textu"))
        assertEquals("gambling", detector.findAny("Hraju online gambling"))
        assertNull(detector.findAny("Cisty text bez problemu"))
    }

    @Test
    fun testCzechAccentsAndCase() {
        // Requirement: Detect keywords with and without accents, case insensitive
        val keywords = listOf("sebevražda", "násilí", "drogy")
        val detector = KeywordDetector(keywords)
        
        // 1. Case Insensitive
        assertEquals("sebevražda", detector.findAny("SEBEVRAŽDA je spatna"))
        
        // 2. Accents
        assertEquals("násilí", detector.findAny("Stop nAsilI na internetu"))
        
        // 3. Substring detection
        assertEquals("drogy", detector.findAny("hledam-drogy-levne"))
    }

    @Test
    fun testOverlappingKeywords() {
        val keywords = listOf("he", "she", "his", "hers")
        val detector = KeywordDetector(keywords)
        
        // Aho-Corasick handles multiple overlaps correctly
        assertNotNull(detector.findAny("ushers")) // matches "she" or "he" or "hers"
    }

    @Test
    fun testEmptyInputs() {
        val detector = KeywordDetector(listOf("danger"))
        assertNull(detector.findAny(""))
        
        val emptyDetector = KeywordDetector(emptyList())
        assertNull(emptyDetector.findAny("something"))
    }
}
