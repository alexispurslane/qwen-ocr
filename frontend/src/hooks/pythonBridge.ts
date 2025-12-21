import { useState, useEffect, useCallback } from 'react'
import { logger } from '../utils/logger'

export interface ProcessingJob {
    jobId: string
    pdfPath: string
    status: 'pending' | 'processing' | 'completed' | 'error' | 'cancelled'
    progress: number
    currentBatch: number
    totalBatches: number
    messages: string[]
    outputTokens: number
    totalPages: number
    totalInputTokens: number
    totalOutputTokens: number
    imagesExtracted: number
    totalCost: number
    error?: string
}

export interface BackendState {
    jobs: ProcessingJob[]
    isProcessing: boolean
}

export function usePythonState<T>(propName: string): T | undefined {
    const [propValue, setPropValue] = useState<T>()

    const subscribeToState = useCallback(() => {
        const handler = (event: any) => {
            logger.debug(`State change event for ${propName}`, { 
                property: event.detail.property, 
                value: event.detail.value 
            })
            if (event.detail.property === propName) {
                logger.debug(`Updating ${propName} state`, { value: event.detail.value })
                setPropValue(event.detail.value)
            }
        }
        window.pywebview.state.addEventListener('change', handler)
        logger.debug(`Subscribed to state changes for ${propName}`)
        return () => window.pywebview.state.removeEventListener('change', handler)
    }, [propName])

    useEffect(() => {
        let cleanup: (() => void) | undefined

        if (window.pywebview?.state) {
            logger.debug(`pywebview.state available, subscribing to ${propName}`)
            cleanup = subscribeToState()
        } else {
            const readyHandler = () => {
                logger.debug(`pywebviewready fired, subscribing to ${propName}`)
                cleanup = subscribeToState()
            }
            window.addEventListener('pywebviewready', readyHandler)
            cleanup = () => window.removeEventListener('pywebviewready', readyHandler)
        }

        return cleanup
    }, [subscribeToState])

    return propValue
}

export function useBackendState(): BackendState | undefined {
    const state = usePythonState<BackendState>('backendState')
    logger.debug('useBackendState returning', { state })
    return state
}

export function usePywebviewReady(): boolean {
    const [ready, setReady] = useState(false)

    useEffect(() => {
        const handlePywebviewReady = () => setReady(true)

        if (window.pywebview?.api) {
            setReady(true)
        } else {
            window.addEventListener('pywebviewready', handlePywebviewReady)
            const interval = setInterval(() => {
                if (window.pywebview?.api) {
                    setReady(true)
                    clearInterval(interval)
                }
            }, 50)

            return () => {
                window.removeEventListener('pywebviewready', handlePywebviewReady)
                clearInterval(interval)
            }
        }
    }, [])

    return ready
}
