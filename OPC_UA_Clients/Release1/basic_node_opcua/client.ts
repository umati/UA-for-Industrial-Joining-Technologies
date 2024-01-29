/**
 * Copyright (c) Sterfive 2023
 */
import {
    OPCUAClient,
    AttributeIds,
    promoteOpaqueStructure,
    ObjectIds,
    NodeClassMask,
    NodeIdLike,
    StatusCodes,
    makeBrowsePath,
    BrowseDirection,
    resolveNodeId,
    sameNodeId,
    NodeId,
    ReferenceDescription
} from 'node-opcua';


const endpointUrl = 'opc.tcp://127.0.0.1:40451';
const nodeId = 'ns=1;s=/ObjectsFolder/TighteningSystem/ResultManagement/Results/Result';


async function main() {
    const client = OPCUAClient.create({
        endpointMustExist: false,
    });
    client.on('backoff', (retry, delay) => {
        console.log('still trying to connect  to ', endpointUrl);
    });
    await client.withSessionAsync(endpointUrl, async (session) => {


        // find the node Id of the Result Object
        const namespaces = await session.readNamespaceArray();
        const nsIJT = namespaces.indexOf('http://opcfoundation.org/UA/IJT/');
        if (nsIJT < 0) {
            console.log('The server do not expose the IJT namespace');
            return;
        }

        // the well known node Id for ResultType  Variable Type in IJK namespace
        const resultTypeNodeId = resolveNodeId(`ns=${nsIJT};i=2001`);

        // the well known node Id for TighteningSystemTypeNodeId  Object Type in IJK namespace
        const tighteningSystemTypeNodeId = resolveNodeId(`ns=${nsIJT};i=1005`);

        // get all TightnessSystem objects in the ObjectFodler
        const thighteningSystems = await findChildrenOfType(ObjectIds.ObjectsFolder, 'Organizes', tighteningSystemTypeNodeId);

        console.log('thighteningSystems found =', thighteningSystems.map((a) => a.browseName.toString()).join(','))
        // explore each one of them.
        for (const thighteningSystem of thighteningSystems) {
            await exploreTighteningSystem(thighteningSystem);
        }


        async function findChildrenOfType(nodeId: NodeIdLike, referenceTypeId: NodeIdLike, typeDefinitionNodeId: NodeId) {

            const resultReferences = await session.browse({
                nodeId: resolveNodeId(nodeId),
                nodeClassMask: NodeClassMask.Variable | NodeClassMask.Object,
                browseDirection: BrowseDirection.Forward,
                includeSubtypes: true,
                referenceTypeId,
                resultMask: 63
            });

            if (resultReferences.statusCode !== StatusCodes.Good || !resultReferences.references) {
                throw new Error('Couldn't browse node ' + nodeId.toString());
            }
           
            // only keep references that are of type ResultType
            resultReferences.references = resultReferences.references?.filter((reference) => sameNodeId(reference.typeDefinition, typeDefinitionNodeId));
            return resultReferences.references;
        }



        async function exploreTighteningSystem(reference: ReferenceDescription): Promise<void> {

            console.log('-------------------------------------------------', reference.browseName.toString());
            console.log('');

            const bpr2 = await session.translateBrowsePath(
                makeBrowsePath(reference.nodeId, `/${nsIJT}:ResultManagement/${nsIJT}:Results`));

            if (bpr2.statusCode !== StatusCodes.Good) {
                console.log('Cannot find the ResultManagement object ');
                return;
            }
            const resultsNodeId = bpr2.targets![0].targetId;

            // find all results in the Results collection

            const resultReferences = await findChildrenOfType(resultsNodeId, 'HasComponent', resultTypeNodeId);


            for (const resultReference of resultReferences) {

                const nodeId = resultReference.nodeId;

                const dataValue = await session.read({
                    nodeId,
                    attributeId: AttributeIds.Value,
                });

                const result = dataValue.value.value;
                await promoteOpaqueStructure(session, [{ value: result.resultContent }]);

                console.log('\n  Tightening result : ', resultReference.browseName.toString());
                console.log(dataValue.toString());

            }

        }


    });
}

main();
