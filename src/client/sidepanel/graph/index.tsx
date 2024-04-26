import { useEffect, useMemo, useState } from "react"
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  Panel,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  useStore,
  type EdgeTypes,
  type NodeChange,
  type NodeTypes
} from "reactflow"

import "reactflow/dist/style.css"
import "./index.css"

import { forceLink, forceManyBody, forceSimulation, forceX, forceY } from "d3-force"
import { GroupIcon, LoaderCircleIcon } from "lucide-react"

import { Button } from "~components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "~components/ui/tooltip"
import type { Relation } from "~types"

import RelationEdge from "./RelationEdge"
import RelationNode from "./RelationNode"
import { collide } from "./utils"

const arrowMarker = {
  type: MarkerType.Arrow,
  width: 24,
  height: 24
}

// helper function to replace spaces with underscores
const get_id = (string: string) => string.replace(/\s+/g, "_")

// helper function to check whether id exists in the list of nodes or edges
const id_exists = (id: string, nodes: any[]) =>
  nodes.find((node) => node.id === id) !== undefined

function RelationGraph({ relations }: { relations: Relation[] }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  const nodeTypes: NodeTypes = useMemo(() => ({ relation: RelationNode }), [])
  // @ts-ignore
  const edgeTypes: EdgeTypes = useMemo(() => ({ relation: RelationEdge }), [])

  const [isGraphInitialized, enableAutoLayout, isAutoLayoutEnabled] = useAutoLayout()

  useEffect(() => {
    if (relations.length === 0) {
      setNodes([])
      setEdges([])
      return
    }

    // cooridnates of the next node; add new nodes to the left bottom corner
    let nextX =
      nodes.length === 0 ? 0 : Math.min(...nodes.map((node) => node.position.x))
    let nextY =
      nodes.length === 0 ? 0 : Math.max(...nodes.map((node) => node.position.y))

    const newNodes = []
    const newEdges = []

    for (const relation of relations) {
      const entityId = get_id(relation.entity)
      const valueId = get_id(relation.value)
      const attributeId = get_id(`${entityId}-${valueId}`)

      // add new nodes if they haven't been added yet
      if (!id_exists(entityId, nodes) && !id_exists(entityId, newNodes)) {
        newNodes.push({
          id: entityId,
          type: "relation",
          position: { x: nextX, y: nextY + 100 },
          data: { label: relation.entity }
        })
      }

      if (!id_exists(valueId, nodes) && !id_exists(valueId, newNodes)) {
        newNodes.push({
          id: valueId,
          type: "relation",
          position: { x: nextX + 200, y: nextY + 100 },
          data: { label: relation.value }
        })
      }

      if (!id_exists(attributeId, edges) && !id_exists(attributeId, newEdges)) {
        newEdges.push({
          id: attributeId,
          type: "relation",
          source: entityId,
          target: valueId,
          data: { label: relation.attribute },
          markerEnd: arrowMarker
        })
      } else {
        // update the label of the edge
        const edge = id_exists(attributeId, edges)
          ? edges.find((edge) => edge.id === attributeId)
          : newEdges.find((edge) => edge.id === attributeId)

        // check if the attribute already exists in the label
        if (
          edge.data.label &&
          !edge.data.label.split(" & ").includes(relation.attribute)
        )
          edge.data.label += " & " + relation.attribute
      }

      nextY += 100 // increment y for the next node
    }

    setNodes([...nodes, ...newNodes])
    setEdges([...edges, ...newEdges])
  }, [relations])

  const onNodesChangeHandler = (changes: NodeChange[]) => {
    onNodesChange(changes)
    for (const change of changes) {
      if (change.type === "dimensions") {
        setTimeout(() => {
          document.getElementById("organize-auto-layout")?.click()
        }, 100)
        break
      }
    }
  }

  // useEffect(() => {
  //   console.error("isAutoLayoutEnabled changed", isAutoLayoutEnabled)
  // }, [isAutoLayoutEnabled])

  return (
    <ReactFlow
      className="rounded-md border border-stone-200 dark:border-stone-800 floatingedges"
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChangeHandler}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      proOptions={{ hideAttribution: true }}
      nodesConnectable={false} // disable editing edges
      fitView>
      <Panel position="top-right">
        {isGraphInitialized && (
          <Tooltip>
            <TooltipTrigger>
              <Button
                id="organize-auto-layout"
                variant="outline"
                size="icon"
                onClick={() => enableAutoLayout()}
                disabled={isAutoLayoutEnabled}>
                {isAutoLayoutEnabled ? (
                  <LoaderCircleIcon className="h-5 w-5 animate-spin" />
                ) : (
                  <GroupIcon className="h-5 w-5" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Organize graph</p>
            </TooltipContent>
          </Tooltip>
        )}
      </Panel>
      <Background />
      <Controls
        className="bg-stone-100 dark:bg-stone-700 rounded-sm"
        position="bottom-right"
      />
    </ReactFlow>
  )
}

function RelationGraphWithProvider({ relations }: { relations: Relation[] }) {
  return (
    <ReactFlowProvider>
      <RelationGraph relations={relations} />
    </ReactFlowProvider>
  )
}

// From https://reactflow.dev/learn/layouting/layouting#d3-force

const simulation = forceSimulation()
  .force("charge", forceManyBody().strength(-1000))
  .force("x", forceX().x(0).strength(0.05))
  .force("y", forceY().y(0).strength(0.05))
  .force("collide", collide())
  .alphaTarget(0.05)
  .stop()

const useAutoLayout = () => {
  const { getNodes, setNodes, getEdges, fitView } = useReactFlow()

  const initialised = useStore((store) =>
    [...store.nodeInternals.values()].every((node) => node.width && node.height)
  )

  const [enabled, setEnabled] = useState(false)

  return useMemo<[boolean, () => void, boolean]>(() => {
    let nodes = getNodes().map((node) => ({
      ...node,
      x: node.position.x,
      y: node.position.y
    }))
    let edges = getEdges().map((edge) => edge)

    let runNextTick = enabled

    const ready = initialised && nodes.length > 0

    // If React Flow hasn't initialised our nodes with a width and height yet, or
    // if there are no nodes in the flow, then we can't run the simulation!
    if (!ready) return [false, () => {}, enabled]

    const enableAutoLayout = () => {
      if (runNextTick) return true // signal that the simulation is already running

      runNextTick = true
      setEnabled(true)
    }

    simulation.nodes(nodes).force(
      "link",
      forceLink(edges)
        // @ts-ignore
        .id((edge) => edge.id)
        .strength(0.05)
        .distance((edge) =>
          // The distance between the nodes is proportional to the length of edge label
          edge.data.label ? edge.data.label.length * 5 + 100 : 100
        )
    )

    // The tick function is called every animation frame while the simulation is
    // running and progresses the simulation one step forward each time.
    const tick = () => {
      // Prepare the nodes for the simulation by fixing the position
      getNodes().forEach((node, i) => {
        // Setting the fx/fy properties of a node tells the simulation to "fix"
        // the node at that position and ignore any forces that would normally
        // cause it to move.

        // @ts-ignore
        nodes[i].fx = node.dragging ? node.position.x : null
        // @ts-ignore
        nodes[i].fy = node.dragging ? node.position.y : null
      })

      // Run the simulation one step forward
      simulation.tick()

      // Update the nodes with the new positions
      setNodes(nodes.map((node) => ({ ...node, position: { x: node.x, y: node.y } })))

      window.requestAnimationFrame(() => {
        // Re-center the viewport
        fitView()

        // If the simulation isn't stopped, schedule another tick.
        if (runNextTick) tick()
      })

      return [true, enableAutoLayout, enabled]
    }

    if (runNextTick) {
      // Start the simulation
      window.requestAnimationFrame(tick)

      // Stop the simulation after the duration
      setTimeout(() => {
        runNextTick = false
        setEnabled(false)
      }, 2000)
    }

    return [true, enableAutoLayout, enabled]
  }, [initialised, enabled])
}

export default RelationGraphWithProvider
