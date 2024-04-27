import { useEffect, useState } from "react"

import { sendToBackground } from "@plasmohq/messaging"

import { ThemeProvider } from "~components/theme-provider"
import { ThemeToggle } from "~components/theme-toggle"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from "~components/ui/accordion"
import { Alert, AlertDescription, AlertTitle } from "~components/ui/alert"
import { Button } from "~components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList
} from "~components/ui/command"
import { Input } from "~components/ui/input"
import { Label } from "~components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "~components/ui/popover"
import { Switch } from "~components/ui/switch"

import "~style.css"

import { download, generateCsv, mkConfig } from "export-to-csv"
import {
  AlertCircleIcon,
  AlertTriangleIcon,
  CheckIcon,
  ChevronsUpDownIcon,
  DownloadIcon,
  LoaderCircleIcon,
  RotateCcwIcon
} from "lucide-react"

import type { RequestBody, ResponseBody } from "~background/messages/process"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger
} from "~components/ui/alert-dialog"
import { ToastAction } from "~components/ui/toast"
import { Toaster } from "~components/ui/toaster"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "~components/ui/tooltip"
import { useToast } from "~components/ui/use-toast"
import { cn, getExportFilename } from "~lib/utils"
import type { Relation } from "~types"
import { CHECK_NETWORK } from "~utils/error"

import RelationGraph from "./graph"

const DEFAULT_MODEL = "gemini/gemini-pro"
// const DEFAULT_MODEL = "together_ai/togethercomputer/llama-2-70b-chat"

const exportCSVConfig = mkConfig({
  quoteStrings: true,
  columnHeaders: ["entity", "attribute", "value"]
})

function IndexSidePanel() {
  // query settings
  const [entity, setEntity] = useState("")
  const [attribute, setAttribute] = useState("")

  // advanced settings
  const [continuous, setContinuous] = useState(false)
  const [model, setModel] = useState(DEFAULT_MODEL)

  // advanced settings accordion
  const [isPopoverOpen, setPopoverOpen] = useState(false)
  const [models, setModels] = useState<string[]>([model])

  // processing state
  const [response, setResponse] = useState<ResponseBody>(null)
  const [previousActions, setPreviousActions] = useState<string[]>([])
  const [results, setResults] = useState<Relation[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // toast for temporary messages
  const { toast } = useToast()

  const fetchModels = async () => {
    try {
      const response = await fetch(`http://localhost:8000/models`)
      const data = await response.json()
      setModels(data)
    } catch (error) {
      console.error("Failed to fetch models", error)
      setModels([model])

      toast({
        icon: <AlertCircleIcon className="h-4 w-4" />,
        description: CHECK_NETWORK,
        action: (
          <ToastAction altText="Retry" onClick={fetchModels}>
            Retry
          </ToastAction>
        )
      })
    }
  }

  // fetch list of available models from the server
  useEffect(() => {
    fetchModels()
  }, [])

  const appendResults = (results: Relation[]) => {
    // remove duplicates
    results = results.filter(
      (v, i, s) =>
        i ===
        s.findIndex(
          (t) =>
            v.entity === t.entity && v.attribute === t.attribute && v.value === t.value
        )
    )
    console.log("Appending results", results)
    setResults((prev) => [...prev, ...results])
  }

  const processPage = async () => {
    // don't start process if entity is not defined
    if (entity === "") return

    setIsLoading(true)

    // send message to background script
    const response = await sendToBackground<RequestBody, ResponseBody>({
      name: "process",
      body: {
        query: {
          entity: entity,
          attribute: attribute === "" ? null : attribute
        },
        model: model,
        continuous: continuous, // enable full autonomous nagivation if true
        previousActions: previousActions
      }
    })

    setResponse(response)
    setIsLoading(false)

    if (response.error != null) {
      toast({
        icon: <AlertCircleIcon className="h-4 w-4" />,
        description: response.error
          ? response.error
          : "Unknown error occurred. Please try again later."
      })
      return
    }

    // append results to previous results
    if (response.error == null && response.results && response.results.length > 0) {
      appendResults(response.results)
    }

    // append latest action to previous actions
    if (response.action) {
      setPreviousActions([...previousActions, response.action])
    }

    // continue processing if continuous mode is enabled
    if (continuous && response.error == null && response.isComplete === false) {
      processPage()
    }
  }

  // check if server responded
  const isServerOnline = models.length > 1

  // check if all required data is ready and server is operational
  const isReady = entity.length > 0 && isServerOnline && !isLoading

  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange>
      <TooltipProvider>
        <div className="flex flex-col items-stretch p-8 gap-4 h-dvh">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold">LociGraph</h1>
            <ThemeToggle />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="entity">Entity</Label>
            <Input
              type="text"
              id="entity"
              placeholder="John Doe"
              disabled={isLoading}
              onChange={(e) => setEntity(e.target.value)}
              value={entity}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="attribute">Attribute</Label>
            <Input
              type="text"
              id="attribute"
              placeholder="studied at"
              disabled={isLoading}
              onChange={(e) => setAttribute(e.target.value)}
              value={attribute}
            />
          </div>

          <Accordion
            type="single"
            collapsible
            className="w-full -mt-3"
            // defaultValue="advanced-settings" // uncomment to open by default
          >
            <AccordionItem value="advanced-settings">
              <AccordionTrigger>Advanced settings</AccordionTrigger>
              <AccordionContent className="flex flex-col gap-4">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="model">Inference model</Label>
                  <Popover open={isPopoverOpen} onOpenChange={setPopoverOpen}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={isPopoverOpen}
                        disabled={!isServerOnline}
                        className="w-full justify-between">
                        {model}
                        <ChevronsUpDownIcon className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[calc(100vw-4rem)] p-0">
                      <Command>
                        <CommandInput placeholder="Search models..." />
                        <CommandList>
                          <CommandEmpty>No models found.</CommandEmpty>
                          <CommandGroup>
                            {models.map((id) => (
                              <CommandItem
                                className="w-full"
                                key={id}
                                value={id}
                                onSelect={(currentValue) => {
                                  if (currentValue !== model) setModel(currentValue)
                                  setPopoverOpen(false)
                                }}>
                                <CheckIcon
                                  className={cn(
                                    "mr-2 h-4 w-4",
                                    id === model ? "opacity-100" : "opacity-0"
                                  )}
                                />
                                <div className="w-full break-all">{id}</div>
                              </CommandItem>
                            ))}
                          </CommandGroup>
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>
                </div>
                <div className="items-center flex gap-4">
                  <Switch
                    id="continuous-mode"
                    disabled={isLoading}
                    checked={continuous}
                    onCheckedChange={(checked) => {
                      setContinuous(Boolean(checked))
                    }}
                  />
                  <Label htmlFor="continuous-mode">Autonomous mode ⚡</Label>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>

          <div className="flex w-full gap-2">
            <Button
              className="flex-1"
              variant={
                isLoading
                  ? "outline"
                  : continuous
                    ? "warning"
                    : isReady
                      ? "primary"
                      : "default"
              }
              disabled={!isReady}
              onClick={() => processPage()}>
              {isLoading ? (
                <div className="flex items-center">
                  <LoaderCircleIcon className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </div>
              ) : response ? (
                response.isComplete ? (
                  "Locate" // processing completed
                ) : (
                  "Continue" // first response received
                )
              ) : (
                "Locate" // not started processing yet
              )}
            </Button>

            {results.length > 0 ||
              (previousActions.length > 0 && (
                <Tooltip>
                  <TooltipTrigger>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="warning" className="px-3">
                          <RotateCcwIcon className="h-4 w-4" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Clear results?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This action cannot be undone. This will permanently delete
                            the current results and session history.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => {
                              // clear results and response
                              setResponse(null)
                              setResults([])
                              setPreviousActions([])
                            }}>
                            Continue
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Clear results</p>
                  </TooltipContent>
                </Tooltip>
              ))}

            {results.length > 0 && (
              <Tooltip>
                <TooltipTrigger>
                  <Button
                    variant="primary"
                    className="px-3"
                    onClick={() => {
                      const csv = generateCsv(exportCSVConfig)(results)
                      download({
                        ...exportCSVConfig,
                        filename: getExportFilename({ entity, attribute })
                      })(csv)
                    }}>
                    <DownloadIcon className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Save results</p>
                </TooltipContent>
              </Tooltip>
            )}
          </div>

          {continuous && (
            <Alert variant="warning">
              <AlertTriangleIcon className="h-4 w-4" />
              <AlertTitle>Warning</AlertTitle>
              <AlertDescription>
                Autonomous mode is enabled. LociGraph will interact with the page
                without your input.
              </AlertDescription>
            </Alert>
          )}

          <div className="flex flex-1 w-full">
            <RelationGraph relations={results} />
          </div>

          <Toaster />
        </div>
      </TooltipProvider>
    </ThemeProvider>
  )
}

export default IndexSidePanel
