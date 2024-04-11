import { AlertCircle } from "lucide-react"
import { useState } from "react"

import { sendToBackground } from "@plasmohq/messaging"

import { Alert, AlertDescription, AlertTitle } from "~components/ui/alert"
import { Button } from "~components/ui/button"
import { Checkbox } from "~components/ui/checkbox"
import { Input } from "~components/ui/input"
import { Label } from "~components/ui/label"

import "~style.css"

import type { RequestBody, ResponseBody } from "~background/messages/process"

function IndexSidePanel() {
  const [entity, setEntity] = useState("Domain")
  const [attribute, setAttribute] = useState("used for")
  const [continuous, setContinuous] = useState(false)

  const [response, setResponse] = useState<ResponseBody>(null)
  const [isLoading, setIsLoading] = useState(false)

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
        continuous: continuous // true to enable full autonomous nagivation
      }
    })

    setResponse(response)
    setIsLoading(false)
  }

  return (
    <div className="flex flex-col items-stretch p-8 gap-4">
      <h1 className="text-2xl font-bold">LociGraph</h1>

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

      <Button
        disabled={isLoading}
        onClick={() => {
          processPage()
        }}>
        Locate
      </Button>

      <div className="items-top flex space-x-2">
        <Checkbox
          id="continuous"
          checked={continuous}
          onCheckedChange={(checked) => {
            setContinuous(Boolean(checked))
          }}
        />
        <div className="grid gap-1.5 leading-none">
          <label
            htmlFor="continuous"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            Enable autonomous mode ⚡
          </label>
          <p className="text-xs text-muted-foreground leading-snug">
            Allow LociGraph to autonomously navigate the web to find the
            information you need.
          </p>
        </div>
      </div>

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
    </div>
  )
}

export default IndexSidePanel
