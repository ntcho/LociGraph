import { sendToContentScript, type PlasmoMessaging } from "@plasmohq/messaging"

import type { ProcessRequestBody, ProcessResponseBody, Relation, RelationQuery } from '~types';
import type {
  RequestBody as ExecuteActionRequestBody,
  ResponseBody as ExecuteActionResponseBody
} from '~contents/execute-action';
import type {
  ResponseBody as WebpageData
} from '~contents/get-webpage-data';

import { getActionString } from "~lib/utils";
import { CHECK_NETWORK, CHECK_EXTENSION } from '~utils/error';

const handler: PlasmoMessaging.MessageHandler<RequestBody, ResponseBody> = async (req, res) => {
  const request = req.body

  // get webpage data from content script
  let webpageData: WebpageData
  try {
    webpageData = await sendToContentScript<any, WebpageData>({
      name: "get-webpage-data"
    })
  } catch (e) {
    console.error(CHECK_EXTENSION, e)
    res.send({ error: CHECK_EXTENSION, isComplete: false })
    return
  }

  // response object to send it to the API server
  const processRequest: ProcessRequestBody = {
    data: webpageData,
    query: request.query,
    previous_actions: request.previousActions
  }
  let process: Response = null;

  try {
    // send request to `process` endpoint
    process = await fetch(`http://localhost:8000/process?model=${request.model}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(processRequest)
    })
  } catch (e) {
    console.error(CHECK_NETWORK, e)
    res.send({ error: CHECK_NETWORK, isComplete: false })
  }

  if (!process.ok) {
    // error while processing
    res.send({ error: process.statusText, isComplete: false })
    return
  }

  // response from the API server
  const processResponse: ProcessResponseBody = await process.json()

  // response object to send it back to the extension page
  const response: ResponseBody = {
    results: processResponse.results,
    confidenceLevel: processResponse.confidence_level,
    action: processResponse.next_action ? getActionString(processResponse.next_action) : null,
    isComplete: false
  }

  if (processResponse.next_action === null) {
    // no next action, process is complete
    res.send({ ...response, isComplete: true })
  } else {
    // next action exists, execute action
    const executeActionResponse = await sendToContentScript<
      ExecuteActionRequestBody, ExecuteActionResponseBody
    >({
      name: "execute-action",
      body: {
        action: processResponse.next_action,
        continuous: request.continuous
      }
    })

    // action executed, continue process
    res.send({ ...response, actionResult: executeActionResponse })
  }
}

export type RequestBody = {
  query: RelationQuery
  model: string
  continuous: boolean
  previousActions?: string[]
}

export type ResponseBody = {
  results?: Relation[]
  action?: string
  actionResult?: ExecuteActionResponseBody
  confidenceLevel?: string
  error?: string
  isComplete: boolean
}

export default handler