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

import {
  AlertCircle,
  AlertTriangle,
  Check,
  ChevronsUpDown,
  LoaderCircle
} from "lucide-react"

import type { RequestBody, ResponseBody } from "~background/messages/process"
import { cn } from "~lib/utils"
import type { Relation } from "~types"

const DEFAULT_MODEL = "gemini/gemini-pro"
// const DEFAULT_MODEL = "together_ai/togethercomputer/llama-2-70b-chat"

function IndexSidePanel() {
  const [entity, setEntity] = useState("")
  const [attribute, setAttribute] = useState("")
  const [continuous, setContinuous] = useState(false)
  const [model, setModel] = useState(DEFAULT_MODEL)

  const [open, setOpen] = useState(false)
  const [models, setModels] = useState<string[]>([model])

  const [response, setResponse] = useState<ResponseBody>(null)
  const [results, setResults] = useState<Relation[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // fetch list of available models from the server
  useEffect(() => {
    ;(async () => {
      try {
        const response = await fetch(`http://localhost:8000/models`)
        const data = await response.json()
        setModels(data)
      } catch (error) {
        console.error("Failed to fetch models", error)
        setModels([model])
      }
    })()
  }, [])

  const appendResult = (result: Relation[]) => {
    setResults((prev) => [...prev, ...result])
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
        continuous: continuous // true to enable full autonomous nagivation
      }
    })

    setResponse(response)
    setIsLoading(false)

    if (
      continuous &&
      response.error === null &&
      response.isComplete === false
    ) {
      if (response.results && response.results.length > 0) {
        appendResult(response.results)
      }
      // process next action
      processPage()
    }
  }

  // check if server responded
  const isServerReady = models.length > 0

  // check if all required data is ready and server is operational
  const isReady = entity.length > 0 && isServerReady && !isLoading

  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange>
      <div className="flex flex-col items-stretch p-8 gap-4">
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
          defaultValue="advanced-settings">
          <AccordionItem value="advanced-settings">
            <AccordionTrigger>Advanced settings</AccordionTrigger>
            <AccordionContent className="flex flex-col gap-4">
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
              <div className="flex flex-col gap-2">
                <Label htmlFor="model">Inference model</Label>
                <Popover open={open} onOpenChange={setOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={open}
                      disabled={!isServerReady}
                      className="w-full justify-between">
                      {model}
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
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
                                if (currentValue !== model)
                                  setModel(currentValue)
                                setOpen(false)
                              }}>
                              <Check
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
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        <Button
          variant={isLoading ? "outline" : continuous ? "warning" : "default"}
          disabled={!isReady}
          onClick={() => {
            processPage()
          }}>
          {isLoading ? (
            <div className="flex items-center">
              <LoaderCircle className="h-4 w-4 mr-2 animate-spin" />
              Processing...
            </div>
          ) : response ? (
            response.isComplete ? (
              "Start over" // processing completed
            ) : (
              "Continue" // first response received
            )
          ) : (
            "Locate" // not started processing yet
          )}
        </Button>

        {!isServerReady && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>
              {response.error
                ? response.error
                : "Unknown error occurred. Please try again later."}
            </AlertDescription>
          </Alert>
        )}

        {continuous && (
          <Alert variant="warning">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Warning</AlertTitle>
            <AlertDescription>
              Autonomous mode is enabled. LociGraph will interact with the page
              without your input.
            </AlertDescription>
          </Alert>
        )}

        {response && response.error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>
              {response.error
                ? response.error
                : "Unknown error occurred. Please try again later."}
            </AlertDescription>
          </Alert>
        )}

        {response && (
          <div>
            <h3>Response</h3>
            <pre>{JSON.stringify(response, null, 2)}</pre>
          </div>
        )}

        {results.length > 0 && ( // TODO: update result visualization
          <div>
            <h3>Results</h3>
            <pre>{JSON.stringify(results, null, 2)}</pre>
          </div>
        )}
      </div>
    </ThemeProvider>
  )
}

export default IndexSidePanel
