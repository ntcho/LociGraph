import { sendToContentScript, type PlasmoMessaging } from "@plasmohq/messaging"

import type { Relation, RelationQuery } from '~types';
import type {
  RequestBody as ExecuteActionRequestBody,
  ResponseBody as ActionResult
} from '~contents/execute-action';
import type {
  ResponseBody as WebpageData
} from '~contents/get-webpage-data';

const handler: PlasmoMessaging.MessageHandler<RequestBody, ResponseBody> = async (req, res) => {
  const query = req.body.query
  const continuous = req.body.continuous

  // get webpage data from content script
  const webpageData = await sendToContentScript<any, WebpageData>({
    name: "get-webpage-data"
  })

  let response = null;

  try {
    response = await fetch("http://localhost:8000/process", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        data: webpageData,
        query: query
      })
    })
  } catch (e) {
    console.error("Error while fetching", e)

    res.send({
      error: "Couldn't connect to the server. Check whether the server is running or try again later."
    })
  }

  const data = await response.json() // { results: Relations[], next_action: Action }

  console.log("data=", data);

  if (data.status_code !== undefined) {
    res.send({ error: `The server couldn't process request. (Error code ${data.status_code})` })
    return
  }

  if (data.next_action === null) {
    res.send({
      results: data.results,
      confidenceLevel: data.confidenceLevel
    })
  } else {
    const actionResults = await sendToContentScript<ExecuteActionRequestBody, ActionResult>({
      name: "execute-action",
      body: {
        action: data.next_action,
        continuous: continuous
      }
    })

    res.send({
      results: data.results,
      actionResult: actionResults,
      confidenceLevel: data.confidenceLevel
    })
  }
}

export type RequestBody = {
  query: RelationQuery
  continuous: boolean
}

export type ResponseBody = {
  results?: Relation[]
  actionResult?: ActionResult
  confidenceLevel?: string
  error?: string
}

export default handler