import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import DeviceOwnerSetup from './DeviceOwnerSetup'
import React from 'react'

// Mock the lucide-react icons
vi.mock('lucide-react', () => ({
    Smartphone: () => <div data-testid="smartphone-icon" />,
    Usb: () => <div data-testid="usb-icon" />,
    CheckCircle: () => <div data-testid="check-icon" />,
    AlertCircle: () => <div data-testid="alert-icon" />,
    Loader: () => <div data-testid="loader-icon" />,
    Computer: () => <div data-testid="computer-icon" />,
    Terminal: () => <div data-testid="terminal-icon" />,
    Settings: () => <div data-testid="settings-icon" />,
    HelpCircle: () => <div data-testid="help-icon" />,
    Trash2: () => <div data-testid="trash-icon" />,
    Shield: () => <div data-testid="shield-icon" />,
}))

// Mock the yume-chan adb libraries
vi.mock('@yume-chan/adb-daemon-webusb', () => ({
    AdbDaemonWebUsbDeviceManager: {
        BROWSER: {
            requestDevice: vi.fn(),
        },
    },
}))

describe('DeviceOwnerSetup', () => {
    const mockOnComplete = vi.fn()
    const mockOnCancel = vi.fn()

    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('renders initial preparation step', () => {
        render(<DeviceOwnerSetup onComplete={mockOnComplete} onCancel={mockOnCancel} />)
        expect(screen.getByText('Příprava zařízení')).toBeDefined()
        expect(screen.getByText('Pokračovat k aktivaci')).toBeDefined()
    })

    it('navigates through steps', async () => {
        render(<DeviceOwnerSetup onComplete={mockOnComplete} onCancel={mockOnCancel} />)

        // Step 1 -> Step 2
        fireEvent.click(screen.getByText('Pokračovat k aktivaci'))
        expect(screen.getByText('Ujistěte se, že máte na telefonu nainstalovanou aplikaci FamilyEye Agent.')).toBeDefined()

        // Step 2 -> Step 3
        fireEvent.click(screen.getByText('Pokračovat'))
        expect(screen.getByText('Připojení k zařízení')).toBeDefined()
    })

    it('shows error if no device is selected', async () => {
        const { AdbDaemonWebUsbDeviceManager } = await import('@yume-chan/adb-daemon-webusb')
        AdbDaemonWebUsbDeviceManager.BROWSER.requestDevice.mockRejectedValue(new Error('No device selected'))

        render(<DeviceOwnerSetup onComplete={mockOnComplete} onCancel={mockOnCancel} />)

        // Go to step 3
        fireEvent.click(screen.getByText('Pokračovat k aktivaci'))
        fireEvent.click(screen.getByText('Pokračovat'))

        // Click connect
        fireEvent.click(screen.getByText('Vybrat zařízení'))

        await waitFor(() => {
            expect(screen.getByText('Nebylo vybráno žádné zařízení.')).toBeDefined()
        })
    })
})
