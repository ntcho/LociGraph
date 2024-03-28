import type { PlasmoMessaging } from "@plasmohq/messaging"

const handler: PlasmoMessaging.MessageHandler = async (req, res) => {
  // const message = await fetch(req.body.id)

  res.send(req.body)
}

export default handler

// TODO: rename ping.ts to something else and add more handlers