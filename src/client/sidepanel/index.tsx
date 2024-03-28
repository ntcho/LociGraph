import { useState } from "react"

import { Button } from "~components/ui/button"
import { Input } from "~components/ui/input"
import { Label } from "~components/ui/label"

import "~style.css"

function IndexSidePanel() {
  const [target, setTarget] = useState("")
  const [relation, setRelation] = useState("")

  const [response, setResponse] = useState(null)

  const processPage = async () => {
    // const response = await fetch("http://localhost:8080/process", {
    //   method: "POST",
    //   headers: {
    //     "Content-Type": "application/json"
    //   },
    //   body: JSON.stringify({ test: "test" })
    // })

    const response = await fetch("https://jsonplaceholder.typicode.com/todos/1")
    const data = await response.json()
    setResponse(data)
  }

  return (
    <div className="flex flex-col items-stretch p-8 gap-4">
      <h1 className="text-2xl font-bold">LociGraph</h1>

      <div className="flex flex-col gap-2">
        <Label htmlFor="target">Target</Label>
        <Input
          type="text"
          id="target"
          placeholder="John Doe"
          onChange={(e) => setTarget(e.target.value)}
          value={target}
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="relation">Relation</Label>
        <Input
          type="text"
          id="relation"
          placeholder="studied at"
          onChange={(e) => setRelation(e.target.value)}
          value={relation}
        />
      </div>

      <Button
        onClick={() => {
          processPage()
        }}>
        Locate
      </Button>

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
