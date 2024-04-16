import { sendToContentScript, type PlasmoMessaging } from "@plasmohq/messaging"

import type { Relation, RelationQuery } from '~types';
import type {
  RequestBody as ExecuteActionRequestBody,
  ResponseBody as ActionResult
} from '~contents/execute-action';
import type {
  ResponseBody as WebpageData
} from '~contents/get-webpage-data';

import { CHECK_NETWORK } from "~utils/error";

const handler: PlasmoMessaging.MessageHandler<RequestBody, ResponseBody> = async (req, res) => {
  const query = req.body.query
  const model = req.body.model
  const continuous = req.body.continuous

  // get webpage data from content script
  const webpageData = await sendToContentScript<any, WebpageData>({
    name: "get-webpage-data"
  })

  let response: Response = null;

  try {
    response = await fetch(`http://localhost:8000/process?model=${model}`, {
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
    console.error(CHECK_NETWORK, e)
    res.send({ error: CHECK_NETWORK, isComplete: false })
  }

  const data = await response.json() // { results: Relations[], next_action: Action }

  console.debug("data =", data);

  if (!response.ok) {
    res.send({ error: response.statusText, isComplete: false })
    return
  }

  if (data.next_action === null) {
    // no next action, process is complete
    res.send({
      results: data.results,
      confidenceLevel: data.confidenceLevel,
      isComplete: true
    })
  } else {
    const actionResult = await sendToContentScript<ExecuteActionRequestBody, ActionResult>({
      name: "execute-action",
      body: {
        action: data.next_action,
        continuous: continuous
      }
    })

    // action executed, process is not complete
    res.send({
      results: data.results,
      actionResult: actionResult,
      confidenceLevel: data.confidenceLevel,
      isComplete: false
    })
  }
}

export type RequestBody = {
  query: RelationQuery
  model: string
  continuous: boolean
}

export type ResponseBody = {
  results?: Relation[]
  actionResult?: ActionResult
  confidenceLevel?: string
  error?: string
  isComplete: boolean
}

export default handler