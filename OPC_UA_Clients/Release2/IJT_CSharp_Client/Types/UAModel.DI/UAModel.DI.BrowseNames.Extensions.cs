// Extensions to UAModel.DI.BrowseNames for browse names used by dependent companion specs
// (e.g., IJT Base) that reference nodes with DI namespace browse names not defined
// in the original DI NodeSet generation.
namespace UAModel.DI;

public static partial class BrowseNames
{
    public const string Maintenance = "Maintenance";
    public const string OperationCounters = "OperationCounters";
}
