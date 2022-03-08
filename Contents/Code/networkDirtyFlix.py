import site
import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    searchPage = PAsearchSites.getSearchSearchURL(siteNum)
    req = PAutils.HTTPRequest(searchPage)
    searchResults = HTML.ElementFromString(req.text)
    siteKey = 0

    xPath = dictValuesFromKey(xPathDB, PAsearchSites.getSearchSiteName(siteNum))

    (siteKey, sitePages) = dictValuesFromKey(siteDB, PAsearchSites.getSearchSiteName(siteNum))

    dirtyFlixTour1 = 'http://dirtyflix.com/index.php/main/show_one_tour/%d' % siteKey
    req = PAutils.HTTPRequest(dirtyFlixTour1)
    tourPageElements1 = HTML.ElementFromString(req.text)

    dirtyFlixTour2 = 'http://dirtyflix.com/index.php/main/show_one_tour/%d/2' % siteKey
    req = PAutils.HTTPRequest(dirtyFlixTour2)
    tourPageElements2 = HTML.ElementFromString(req.text)

    for idx in range (2, sitePages):
        for searchResult in searchResults.xpath('//div[@class="movie-block"]'):
            titleNoFormatting = PAutils.parseTitle(searchResult.xpath(xPath[0])[0].text_content().strip(), siteNum)

            movieID = searchResult.xpath('.//li/img/@src')[0]
            m = re.search(r'(?<=tour_thumbs/).*(?=\/)', movieID)
            if m:
                curID = PAutils.Encode(m.group(0))

            try:
                tourPageElements = tourPageElements1.xpath('//div[@class="thumbs-item"][.//*[contains(@src, "%s")]]' % m.group(0))[0]
                date = tourPageElements.xpath('.//span[@class="added"]')[0].text_content().strip()
            except:
                try:
                    tourPageElements = tourPageElements2.xpath('//div[@class="thumbs-item"][.//*[contains(@src, "%s")]]' % m.group(0))[0]
                    date = tourPageElements.xpath('.//span[@class="added"]')[0].text_content().strip()
                except:
                    date = ''

            if date:
                releaseDate = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
            else:
                releaseDate = searchData.dateFormat() if searchData.date else ''

            score = 80 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

            if searchData.date:
                score = score - Util.LevenshteinDistance(searchData.date, releaseDate)

            results.Append(MetadataSearchResult(id='%s|%d|%s|%s' % (curID, siteNum, releaseDate, PAutils.Encode(searchPage)), name='%s [%s] %s' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum), releaseDate), score=score, lang=lang))

            if int(score) == 80:
                break
        else:
            searchPage = '%s%d' % (PAsearchSites.getSearchSearchURL(siteNum), idx)
            req = PAutils.HTTPRequest(searchPage)
            searchResults = HTML.ElementFromString(req.text)
            continue
        break

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    metadata_id = str(metadata.id).split('|')
    movieID = PAutils.Decode(metadata_id[0])
    sceneDate = metadata_id[2]
    searchPageURL = PAutils.Decode(metadata_id[3])

    req = PAutils.HTTPRequest(searchPageURL)
    detailsPageElements = HTML.ElementFromString(req.text).xpath('//div[@class="movie-block"][.//*[contains(@src, "%s")]]' % movieID)[0]

    xPath = dictValuesFromKey(xPathDB, PAsearchSites.getSearchSiteName(siteNum))

    # Title
    metadata.title = PAutils.parseTitle(detailsPageElements.xpath(xPath[0])[0].text_content().strip(), siteNum)

    # Summary
    metadata.summary = detailsPageElements.xpath(xPath[1])[0].text_content().strip()

    # Studio
    metadata.studio = 'Dirty Flix'

    # Collections / Tagline
    metadata.collections.clear()
    tagline = PAsearchSites.getSearchSiteName(siteNum)
    metadata.tagline = tagline
    metadata.collections.add(tagline)

    # Release Date
    if sceneDate:
        date_object = parse(sceneDate)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    movieGenres.clearGenres()
    genres = dictValuesFromKey(genresDB, PAsearchSites.getSearchSiteName(siteNum))
    for genreName in genres:
        movieGenres.addGenre(genreName)

    # Actors
    movieActors.clearActors()
    actors = dictKeyFromValues(sceneActorsDB, movieID)
    for actor in actors:
        actorName = actor.strip()
        actorPhotoURL = ''

        movieActors.addActor(actorName, actorPhotoURL)

    # Posters
    art.append(detailsPageElements.xpath('.//img/@src')[0])

    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                image = PAutils.HTTPRequest(posterUrl)
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if width > 1:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                if width > height:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata


def dictValuesFromKey(dictDB, identifier):
    for k, values in dictDB.items():
        keys = list(k) if type(k) == tuple else [k]
        for key in keys:
            if key.lower() == identifier.replace(' ', '').lower():
                return values
    return


def dictKeyFromValues(dictDB, identifier):
    values = []
    for key, value in dictDB.items():
        for item in value:
            if item.lower() == identifier.lower():
                values.append(key)
                break
    return values


genresDB = {
    'TrickYourGF': ['Girlfriend', 'Revenge'],
    'MakeHimCuckold': ['Cuckold'],
    'SheIsNerdy': ['Glasses', 'Nerd'],
    'TrickyAgent': ['Agent', 'Casting'],
}


xPathDB = {
    ('TrickYourGF', 'MakeHimCuckold'): ['.//a[contains(@class, "link")]', './/div[@class="description"]'],
    'SheIsNerdy': ['.//a[contains(@class, "title")]', './/div[@class="description"]'],
    'TrickyAgent': ['.//h3', './/div[@class="text"]'],
}


# [Dirty Flix Tour Number, Number of Active Search Pages]
siteDB = {
    'TrickYourGF': [7, 4],
    'MakeHimCuckold': [9, 5],
    'SheIsNerdy': [10, 12],
    'TrickyAgent': [11, 4],
}


sceneActorsDB = {
    'Adina': ['darygf050'],
    'Alaina Dawson': ['crygf009'],
    'Aggie': ['wrygf726'],
    'Amalia Davis': ['wnc1560'],
    'Amber Daikiri': ['wrygf508'],
    'Angie Koks': ['wrygf911'],
    'Annika Seren': ['wrygf451'],
    'Aruna Aghora': ['wrygf900'],
    'Carmen Fox': ['wnc833'],
    'Chloe Blue': ['wrygf526'],
    'Christi Cats': ['wrygf553'],
    'Darcy Dark': ['wnc1590'],
    'Elin Holm': ['wnc1453'],
    'Eva': ['wrygf865'],
    'Evelyn Cage': ['wrygf651'],
    'Emma': ['wrygf634'],
    'Gina Gerson': ['wrygf622'],
    'Gisha Forza': ['wrygf1442'],
    'Gloria Miller': ['wrygf738'],
    'Glorie': ['darygf052'],
    'Foxy Di': ['wrygf886', 'wrygf828'],
    'Hanna Rey': ['wnc1550'],
    'Inga Zolva': ['wrygf747'],
    'Iris Kiss': ['snc165', 'wnc1637'],
    'Iva Zan': ['wrygf536'],
    'Jenny Manson': ['wtag1324', 'wfc1302'],
    'Jessica Malone': ['wrygf1078'],
    'Jessica Rox': ['prygf138'],
    'Kendra Cole': ['hrygf002'],
    'Kiara Knight': ['crygf002'],
    'Kira Stone': ['snc171'],
    'Kirsten': ['wrygf499'],
    'Lina Napoli': ['wrygf760'],
    'Andrea Sun': ['darygf057'],
    'Lizaveta Kay': ['wrygf733'],
    'Masha B': ['wrygf485'],
    'Michelle Can': ['wfc1392'],
    'Milka Feer': ['snc214'],
    'Molly Manson': ['crygf013'],
    'Monica Rise': ['crygf011'],
    'Liona Levi': ['wrygf663'],
    'Oliva Grace': ['wrygf991'],
    'Rebecca Rainbow': ['wrygf1201'],
    'Rita': ['wtag1232'],
    'Rita Jalace': ['wrygf633'],
    'Rita Milan': ['wrygf870'],
    'Serpente Edita': ['wrygf930'],
    'Shrima Malati': ['wrygf993'],
    'Sonja': ['wrygf648'],
    'Stacy Snake': ['wrygf427'],
    'Veronika Fare': ['wnc1315'],
}
