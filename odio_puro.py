def setFullDataFrame(self, be_df:DataFrame, cit_df:DataFrame) -> DataFrame: #auxiliary function
        #method created to avoid repeating code on the constructors of Citation entities and their subclasses
        #it merges the BE and Citation in a way that facilitates the creation of hasCitingEntity and hasCitedEntity
        if not be_df.empty:
            mom_be = be_df
            prefix = "https://opencitations.net/entity/"
            mom_be["internalId"] = mom_be["internalId"].apply(lambda x: prefix + x) #adds the prefix in front of the elements of the internalId column in the bibliographic entries dataframe,
                                                                                    #so that it can be the same as the ids found in the citing and cited columns of the citations dataframe
            full_df = cit_df
            
            citing_df = mom_be.rename(columns={"internalId":"internalId_citing",
                                               "title":"title_citing",
                                               "author":"author_citing",
                                               "pub_date":"pub_date_citing",
                                               "venue":"venue_citing",
                                               "id":"id_citing"})
            
            full_df = merge(full_df, citing_df, left_on="citing", right_on="internalId_citing", how="inner") #merges the Citations dataframe with a BE one on the "citing" column,
                                                                                                        #and the columns of the latter have been modified to make them recognizable
            cited_df = mom_be.rename(columns={"internalId":"internalId_cited",
                                              "title":"title_cited",
                                              "author":"author_cited",
                                              "pub_date":"pub_date_cited",
                                              "venue":"venue_cited",
                                              "id":"id_cited"})
            
            full_df = merge(full_df, cited_df, left_on="cited", right_on="internalId_cited", how="inner") #merges the Citations dataframe with a BE one on the "cited" column,
                                                                                                    #and the columns of the latter have been modified to make them recognizable
        else:
            df_cit = cit_df
            df_empty = DataFrame(columns=["oci", "creation", "citing","id_citing", "cited", "id_cited", "timespan"])
            full_df = concat([df_empty, df_cit])
        return full_df
