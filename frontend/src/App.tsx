import { useCallback, useState, useEffect } from "react";
import { Layout, Model } from "flexlayout-react";
import "flexlayout-react/style/light.css";
import * as Tabs from "@radix-ui/react-tabs";
import * as ScrollArea from "@radix-ui/react-scroll-area";
import * as Progress from "@radix-ui/react-progress";
import * as Separator from "@radix-ui/react-separator";
import {
    UploadIcon,
    FileTextIcon,
    ImageIcon,
    GearIcon,
    CrossCircledIcon,
    CheckCircledIcon,
    ClockIcon,
    ReloadIcon,
} from "@radix-ui/react-icons";
import { useBackendState, usePywebviewReady } from "./hooks/pythonBridge";
import { logger } from "./utils/logger";
import "./App.css";

interface TabNode {
    getComponent(): string;
}

const json = {
    global: {
        tabEnableClose: false,
    },
    borders: [
        {
            type: "border",
            location: "left",
            children: [
                {
                    type: "tab",
                    name: "File Browser",
                    component: "fileBrowser",
                },
            ],
        },
        {
            type: "border",
            location: "bottom",
            children: [
                {
                    type: "tab",
                    name: "Status",
                    component: "status",
                },
            ],
        },
    ],
    layout: {
        type: "row",
        weight: 100,
        children: [
            {
                type: "tabset",
                weight: 50,
                children: [
                    {
                        type: "tab",
                        name: "Jobs",
                        component: "jobs",
                    },
                ],
            },
            {
                type: "tabset",
                weight: 50,
                children: [
                    {
                        type: "tab",
                        name: "Output",
                        component: "output",
                    },
                ],
            },
        ],
    },
};

function App() {
    const [model] = useState(() => {
        logger.debug("Creating FlexLayout model from JSON configuration");
        return Model.fromJson(json);
    });
    const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
    const backendState = useBackendState();
    const pywebviewReady = usePywebviewReady();

    // Log state changes for debugging
    useEffect(() => {
        logger.debug("Backend state updated", {
            jobsCount: backendState?.jobs?.length || 0,
            isProcessing: backendState?.isProcessing || false,
            jobs: backendState?.jobs?.map(job => ({
                id: job.jobId,
                status: job.status,
                progress: job.progress,
                currentBatch: job.currentBatch,
                totalBatches: job.totalBatches
            }))
        });
    }, [backendState]);

    useEffect(() => {
        logger.debug("Selected job ID changed", { selectedJobId });
    }, [selectedJobId]);

    useEffect(() => {
        if (pywebviewReady) {
            logger.info("PyWebview ready - frontend can communicate with backend");
        }
    }, [pywebviewReady]);

    const factory = useCallback(
        (node: any) => {
            const component = node.getComponent();

            switch (component) {
                case "fileBrowser":
                    return (
                        <div className="p-4 h-full flex flex-col gap-4">
                            <h3 className="text-sm font-semibold">PDF Files</h3>
                            <button
                                className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm w-full justify-center"
                                onClick={async () => {
                                    logger.info("User clicked 'Select & Process PDF' button - calling backend select_pdf_file()");
                                    try {
                                        const result = await window.pywebview.api.select_pdf_file();
                                        logger.info("Backend select_pdf_file() returned", { result });
                                        if (result) {
                                            logger.info(`File selected: ${result} - calling backend start_processing()`);
                                            const jobId = await window.pywebview.api.start_processing(result);
                                            logger.info("Backend start_processing() returned job ID", { jobId });
                                        } else {
                                            logger.info("No file selected by user");
                                        }
                                    } catch (error) {
                                        logger.error("Failed to select/process file", error);
                                    }
                                }}
                            >
                                <UploadIcon /> Select & Process PDF
                            </button>
                            <ScrollArea.Root className="flex-1 w-full">
                                <ScrollArea.Viewport className="w-full h-full">
                                    <div className="flex flex-col gap-2">
                                        {backendState?.jobs.map((job) => (
                                            <div
                                                key={job.jobId}
                                                className="p-3 bg-gray-100 rounded-md border border-gray-200"
                                            >
                                                <div className="flex flex-col gap-1">
                                                    <div className="text-sm font-medium truncate">
                                                        {job.pdfPath.split("/").pop()}
                                                    </div>
                                                    <div className="text-xs text-gray-500">{job.status}</div>
                                                    {job.status === "processing" && (
                                                        <Progress.Root
                                                            className="w-full h-2 bg-gray-200 rounded-full overflow-hidden"
                                                            value={job.progress}
                                                        >
                                                            <Progress.Indicator
                                                                className="h-full bg-blue-600 transition-all"
                                                                style={{ width: `${job.progress}%` }}
                                                            />
                                                        </Progress.Root>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </ScrollArea.Viewport>
                                <ScrollArea.Scrollbar orientation="vertical">
                                    <ScrollArea.Thumb />
                                </ScrollArea.Scrollbar>
                                <ScrollArea.Scrollbar orientation="horizontal">
                                    <ScrollArea.Thumb />
                                </ScrollArea.Scrollbar>
                                <ScrollArea.Corner />
                            </ScrollArea.Root>
                        </div>
                    );

                case "jobs":
                    return (
                        <div className="p-4 h-full flex flex-col gap-4">
                            <h3 className="text-sm font-semibold">Processing Jobs</h3>
                            <ScrollArea.Root className="flex-1 w-full">
                                <ScrollArea.Viewport className="w-full h-full">
                                    <div className="flex flex-col gap-3">
                                        {backendState?.jobs.map((job) => (
                                            <div
                                                key={job.jobId}
                                                className={`p-4 bg-white rounded-lg border shadow-sm cursor-pointer transition-all ${
                                                    selectedJobId === job.jobId
                                                        ? "border-blue-500 ring-2 ring-blue-200"
                                                        : "border-gray-200 hover:border-gray-300"
                                                }`}
                                                onClick={() => setSelectedJobId(job.jobId)}
                                            >
                                                <div className="flex flex-col gap-2">
                                                    <div className="flex justify-between items-center">
                                                        <div className="text-sm font-medium">
                                                            {job.pdfPath.split("/").pop()}
                                                        </div>
                                                        <JobStatusIcon status={job.status} />
                                                    </div>
                                                    <div className="text-xs text-gray-500">
                                                        ID: {job.jobId.slice(0, 8)}
                                                    </div>
                                                    {job.status === "processing" && (
                                                        <div className="mt-2">
                                                            <Progress.Root
                                                                className="w-full h-2 bg-gray-200 rounded-full overflow-hidden"
                                                                value={job.progress}
                                                            >
                                                                <Progress.Indicator
                                                                    className="h-full bg-blue-600 transition-all"
                                                                    style={{ width: `${job.progress}%` }}
                                                                />
                                                            </Progress.Root>
                                                        </div>
                                                    )}
                                                    <div className="flex flex-col gap-1 mt-2">
                                                        {job.messages.slice(-3).map((msg, idx) => (
                                                            <div
                                                                key={idx}
                                                                className="text-xs text-gray-600"
                                                            >
                                                                {msg}
                                                            </div>
                                                        ))}
                                                    </div>
                                                    {job.status === "processing" && (
                                                        <button
                                                            className="inline-flex items-center justify-center px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700 transition-colors mt-2 self-start"
                                                            onClick={async (e) => {
                                                                e.stopPropagation();
                                                                logger.info(`User requested cancellation for job ${job.jobId.slice(0, 8)}... - calling backend cancel_job()`);
                                                                try {
                                                                    await window.pywebview.api.cancel_job(job.jobId);
                                                                    logger.info(`Backend cancel_job() completed for job ${job.jobId.slice(0, 8)}...`);
                                                                } catch (error) {
                                                                    logger.error(`Failed to cancel job ${job.jobId.slice(0, 8)}...`, error);
                                                                }
                                                            }}
                                                        >
                                                            Cancel
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </ScrollArea.Viewport>
                                <ScrollArea.Scrollbar orientation="vertical">
                                    <ScrollArea.Thumb />
                                </ScrollArea.Scrollbar>
                                <ScrollArea.Scrollbar orientation="horizontal">
                                    <ScrollArea.Thumb />
                                </ScrollArea.Scrollbar>
                                <ScrollArea.Corner />
                            </ScrollArea.Root>
                        </div>
                    );

                case "output":
                    const selectedJob = backendState?.jobs.find(
                        (j) => j.jobId === selectedJobId
                    );
                    return (
                        <div className="p-4 h-full flex flex-col gap-4">
                            <h3 className="text-sm font-semibold">
                                {selectedJob
                                    ? `Output: ${selectedJob.pdfPath.split("/").pop()}`
                                    : "Output (Select a job)"}
                            </h3>
                            {selectedJob && (
                                <Tabs.Root defaultValue="markdown" className="flex-1">
                                    <Tabs.List className="flex border-b border-gray-200">
                                        <Tabs.Trigger
                                            value="markdown"
                                            className="px-4 py-2 text-sm hover:bg-gray-100 data-[state=active]:border-b-2 data-[state=active]:border-blue-600 data-[state=active]:text-blue-600"
                                        >
                                            Markdown
                                        </Tabs.Trigger>
                                        <Tabs.Trigger
                                            value="stats"
                                            className="px-4 py-2 text-sm hover:bg-gray-100 data-[state=active]:border-b-2 data-[state=active]:border-blue-600 data-[state=active]:text-blue-600"
                                        >
                                            Statistics
                                        </Tabs.Trigger>
                                    </Tabs.List>

                                    <div className="pt-3 h-full">
                                        <Tabs.Content value="markdown" className="h-full">
                                            <ScrollArea.Root className="h-full w-full">
                                                <ScrollArea.Viewport className="w-full h-full">
                                                    <div className="p-2 bg-gray-100 rounded-md h-full">
                                                        <pre className="text-sm whitespace-pre-wrap font-mono h-full overflow-auto">
                                                            {selectedJob.status === "completed"
                                                                ? "[Output would be displayed here]"
                                                                : "Processing..."}
                                                        </pre>
                                                    </div>
                                                </ScrollArea.Viewport>
                                                <ScrollArea.Scrollbar orientation="vertical">
                                                    <ScrollArea.Thumb />
                                                </ScrollArea.Scrollbar>
                                                <ScrollArea.Scrollbar orientation="horizontal">
                                                    <ScrollArea.Thumb />
                                                </ScrollArea.Scrollbar>
                                            </ScrollArea.Root>
                                        </Tabs.Content>

                                        <Tabs.Content value="stats">
                                            <div className="grid grid-cols-2 gap-4">
                                                <StatCard
                                                    label="Pages"
                                                    value={selectedJob.totalPages.toString()}
                                                />
                                                <StatCard
                                                    label="Images Extracted"
                                                    value={selectedJob.imagesExtracted.toString()}
                                                />
                                                <StatCard
                                                    label="Input Tokens"
                                                    value={selectedJob.totalInputTokens.toLocaleString()}
                                                />
                                                <StatCard
                                                    label="Output Tokens"
                                                    value={selectedJob.totalOutputTokens.toLocaleString()}
                                                />
                                                <StatCard
                                                    label="Total Cost"
                                                    value={`$${selectedJob.totalCost.toFixed(4)}`}
                                                />
                                                <StatCard
                                                    label="Status"
                                                    value={selectedJob.status}
                                                />
                                            </div>
                                        </Tabs.Content>
                                    </div>
                                </Tabs.Root>
                            )}
                        </div>
                    );

                case "status":
                    return (
                        <div className="p-3 h-full flex flex-col gap-2">
                            <div className="flex justify-between items-center">
                                <div className="text-sm font-medium">Status</div>
                                {backendState?.isProcessing && (
                                    <ReloadIcon className="animate-spin" />
                                )}
                            </div>
                            <ScrollArea.Root className="flex-1 w-full">
                                <ScrollArea.Viewport className="w-full h-full">
                                    <div className="space-y-2">
                                        {backendState?.jobs
                                            .filter((j) => j.status === "processing")
                                            .map((job) => (
                                                <div key={job.jobId} className="mb-2">
                                                    <div className="text-xs font-medium mb-1">
                                                        {job.pdfPath.split("/").pop()}
                                                    </div>
                                                    <Progress.Root
                                                        className="w-full h-2 bg-gray-200 rounded-full overflow-hidden"
                                                        value={job.progress}
                                                    >
                                                        <Progress.Indicator
                                                            className="h-full bg-blue-600 transition-all"
                                                            style={{ width: `${job.progress}%` }}
                                                        />
                                                    </Progress.Root>
                                                    <div className="text-xs text-gray-500">
                                                        Batch {job.currentBatch + 1} of {job.totalBatches}
                                                    </div>
                                                </div>
                                            ))}
                                    </div>
                                </ScrollArea.Viewport>
                                <ScrollArea.Scrollbar orientation="vertical">
                                    <ScrollArea.Thumb />
                                </ScrollArea.Scrollbar>
                            </ScrollArea.Root>
                        </div>
                    );

                default:
                    return <div>Unknown component: {component}</div>;
            }
        },
        [backendState, selectedJobId]
    );

    if (!pywebviewReady) {
        logger.debug("Rendering loading screen - pywebview not ready yet");
        return (
            <div className="h-screen w-screen flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <ReloadIcon className="w-12 h-12 animate-spin" />
                    <div className="text-lg">Loading OCR Workbench...</div>
                </div>
            </div>
        );
    }

    logger.debug("Rendering main application layout");

    return (
        <div style={{ height: "100vh", width: "100vw" }}>
            <Layout
                model={model}
                factory={factory}
                onRenderTab={(node: TabNode, renderValues: any) => {
                    const icons: Record<string, React.ReactNode> = {
                        fileBrowser: <UploadIcon />,
                        jobs: <FileTextIcon />,
                        output: <FileTextIcon />,
                        status: <GearIcon />,
                    };
                    renderValues.content = (
                        <div className="flex items-center gap-1">
                            {icons[node.getComponent()]}
                            <span>{node.getName()}</span>
                        </div>
                    );
                }}
            />
        </div>
    );
}

function JobStatusIcon({ status }: { status: string }) {
    const icons: Record<string, React.ReactNode> = {
        completed: <CheckCircledIcon className="text-green-600" />,
        error: <CrossCircledIcon className="text-red-600" />,
        processing: <ReloadIcon className="animate-spin" />,
        pending: <ClockIcon className="text-gray-500" />,
        cancelled: <CrossCircledIcon className="text-orange-600" />,
    };
    
    useEffect(() => {
        logger.debug(`Rendering status icon for job status: ${status}`);
    }, [status]);
    
    return <>{icons[status] || null}</>;
}

function StatCard({ label, value }: { label: string; value: string }) {
    return (
        <div className="p-4 bg-white border border-gray-200 rounded-lg">
            <div className="flex flex-col gap-1">
                <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
                <div className="text-2xl font-bold">{value}</div>
            </div>
        </div>
    );
}

export default App;
