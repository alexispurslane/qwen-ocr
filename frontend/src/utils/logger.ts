// Shared logger for frontend components
// Mirrors backend logging patterns for end-to-end tracing

const colors = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[36m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    gray: '\x1b[90m'
};

const logLevels = {
    info: { color: colors.green, prefix: 'FE-INFO' },
    debug: { color: colors.cyan, prefix: 'FE-DEBUG' },
    warn: { color: colors.yellow, prefix: 'FE-WARN' },
    error: { color: colors.red, prefix: 'FE-ERROR' }
};

export const logger = {
    info: (message: string, data?: any) => {
        const timestamp = new Date().toISOString();
        const { color, prefix } = logLevels.info;
        const logMessage = `${color}[${timestamp}] [${prefix}]${colors.reset} ${message}`;
        console.log(logMessage, data ? JSON.stringify(data, null, 2) : '');
    },
    
    debug: (message: string, data?: any) => {
        const timestamp = new Date().toISOString();
        const { color, prefix } = logLevels.debug;
        const logMessage = `${color}[${timestamp}] [${prefix}]${colors.reset} ${message}`;
        console.log(logMessage, data ? JSON.stringify(data, null, 2) : '');
    },
    
    warn: (message: string, data?: any) => {
        const timestamp = new Date().toISOString();
        const { color, prefix } = logLevels.warn;
        const logMessage = `${color}[${timestamp}] [${prefix}]${colors.reset} ${message}`;
        console.warn(logMessage, data ? JSON.stringify(data, null, 2) : '');
    },
    
    error: (message: string, error?: any) => {
        const timestamp = new Date().toISOString();
        const { color, prefix } = logLevels.error;
        const logMessage = `${color}[${timestamp}] [${prefix}]${colors.reset} ${message}`;
        console.error(logMessage, error ? JSON.stringify(error, null, 2) : '');
    }
};